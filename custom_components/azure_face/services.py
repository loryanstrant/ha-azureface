"""Services for the Azure Face integration."""
import asyncio
import base64
import io
import logging
from typing import Any, Dict
import aiohttp

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.components.camera import async_get_image

from .azure_client import AzureFaceAPIError
from .const import (
    DOMAIN,
    SERVICE_RECOGNIZE_FACE,
    SERVICE_TRAIN_PERSON,
    SERVICE_CREATE_PERSON_GROUP,
    SERVICE_TRAIN_GROUP,
    SERVICE_CREATE_PERSON,
    SERVICE_UPLOAD_PERSON_IMAGE,
    SERVICE_GET_TRAINING_STATUS,
    SERVICE_LIST_PERSONS,
    SERVICE_RECOGNIZE_FACE_SCHEMA,
    SERVICE_TRAIN_PERSON_SCHEMA,
    SERVICE_CREATE_PERSON_GROUP_SCHEMA,
    SERVICE_TRAIN_GROUP_SCHEMA,
    SERVICE_CREATE_PERSON_SCHEMA,
    SERVICE_UPLOAD_PERSON_IMAGE_SCHEMA,
    SERVICE_GET_TRAINING_STATUS_SCHEMA,
    SERVICE_LIST_PERSONS_SCHEMA,
    CONF_CAMERA_ENTITY,
    CONF_PERSON_GROUP_ID,
    ERROR_NO_FACE_DETECTED,
    ERROR_MULTIPLE_FACES,
)
from .helpers import get_azure_face_client, get_person_group_id

_LOGGER = logging.getLogger(__name__)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up the Azure Face services."""
    
    async def async_recognize_face(call: ServiceCall) -> None:
        """Recognize faces in camera image."""
        camera_entity = call.data[CONF_CAMERA_ENTITY]
        confidence_threshold = call.data.get("confidence_threshold", 0.7)
        
        try:
            # Get the Azure Face client
            client = await get_azure_face_client(hass)
            person_group_id = await get_person_group_id(hass)
            
            # Get image from camera
            image_data = await async_get_image(hass, camera_entity)
            if not image_data:
                raise HomeAssistantError(f"Could not get image from camera {camera_entity}")
            
            # Detect faces
            faces = await client.detect_faces(image_data.content)
            
            if not faces:
                _LOGGER.warning("No faces detected in image")
                hass.bus.async_fire(
                    f"{DOMAIN}_recognition_result",
                    {
                        "camera_entity": camera_entity,
                        "faces_detected": 0,
                        "identifications": [],
                        "error": ERROR_NO_FACE_DETECTED,
                    },
                )
                return
            
            if len(faces) > 1:
                _LOGGER.warning("Multiple faces detected in image")
                hass.bus.async_fire(
                    f"{DOMAIN}_recognition_result",
                    {
                        "camera_entity": camera_entity,
                        "faces_detected": len(faces),
                        "identifications": [],
                        "error": ERROR_MULTIPLE_FACES,
                    },
                )
                return
            
            # Extract face IDs
            face_ids = [face["faceId"] for face in faces]
            
            # Identify faces
            identifications = await client.identify_faces(
                face_ids, person_group_id, confidence_threshold=confidence_threshold
            )
            
            # Process results
            results = []
            for i, identification in enumerate(identifications):
                face_data = faces[i]
                result = {
                    "face_id": identification["faceId"],
                    "face_attributes": face_data.get("faceAttributes", {}),
                    "candidates": [],
                }
                
                for candidate in identification.get("candidates", []):
                    result["candidates"].append({
                        "person_id": candidate["personId"],
                        "confidence": candidate["confidence"],
                    })
                
                results.append(result)
            
            # Fire event with results
            hass.bus.async_fire(
                f"{DOMAIN}_recognition_result",
                {
                    "camera_entity": camera_entity,
                    "faces_detected": len(faces),
                    "identifications": results,
                },
            )
            
            _LOGGER.info(
                "Face recognition completed for %s. Detected %d faces, identified %d candidates",
                camera_entity,
                len(faces),
                sum(len(r["candidates"]) for r in results),
            )
            
        except AzureFaceAPIError as err:
            _LOGGER.error("Azure Face API error during recognition: %s", err)
            hass.bus.async_fire(
                f"{DOMAIN}_recognition_result",
                {
                    "camera_entity": camera_entity,
                    "faces_detected": 0,
                    "identifications": [],
                    "error": str(err),
                },
            )
            raise HomeAssistantError(f"Azure Face API error: {err}") from err
        
        except Exception as err:
            _LOGGER.error("Unexpected error during face recognition: %s", err)
            raise HomeAssistantError(f"Face recognition failed: {err}") from err

    async def async_train_person(call: ServiceCall) -> None:
        """Add training image for a person."""
        person_id = call.data["person_id"]
        image_url = call.data["image_url"]
        detection_model = call.data.get("detection_model", "detection_03")
        
        try:
            # Get the Azure Face client
            client = await get_azure_face_client(hass)
            person_group_id = await get_person_group_id(hass)
            
            # Download image from URL
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        raise HomeAssistantError(f"Failed to download image from {image_url}")
                    image_data = await response.read()
            
            # Add face to person
            result = await client.add_person_face(
                person_group_id, person_id, image_data, detection_model
            )
            
            # Fire event with result
            hass.bus.async_fire(
                f"{DOMAIN}_training_result",
                {
                    "person_id": person_id,
                    "persisted_face_id": result["persistedFaceId"],
                    "action": "face_added",
                },
            )
            
            _LOGGER.info("Successfully added training face for person %s", person_id)
            
        except AzureFaceAPIError as err:
            _LOGGER.error("Azure Face API error during training: %s", err)
            hass.bus.async_fire(
                f"{DOMAIN}_training_result",
                {
                    "person_id": person_id,
                    "action": "face_added",
                    "error": str(err),
                },
            )
            raise HomeAssistantError(f"Azure Face API error: {err}") from err
        
        except Exception as err:
            _LOGGER.error("Unexpected error during person training: %s", err)
            raise HomeAssistantError(f"Person training failed: {err}") from err

    async def async_create_person_group(call: ServiceCall) -> None:
        """Create a new person group."""
        person_group_id = call.data[CONF_PERSON_GROUP_ID]
        name = call.data["name"]
        user_data = call.data.get("user_data")
        recognition_model = call.data.get("recognition_model", "recognition_04")
        
        try:
            # Get the Azure Face client
            client = await get_azure_face_client(hass)
            
            # Create person group
            await client.create_person_group(
                person_group_id, name, user_data, recognition_model
            )
            
            # Fire event with result
            hass.bus.async_fire(
                f"{DOMAIN}_group_management",
                {
                    "person_group_id": person_group_id,
                    "action": "group_created",
                    "name": name,
                },
            )
            
            _LOGGER.info("Successfully created person group %s", person_group_id)
            
        except AzureFaceAPIError as err:
            _LOGGER.error("Azure Face API error during group creation: %s", err)
            hass.bus.async_fire(
                f"{DOMAIN}_group_management",
                {
                    "person_group_id": person_group_id,
                    "action": "group_created",
                    "error": str(err),
                },
            )
            raise HomeAssistantError(f"Azure Face API error: {err}") from err
        
        except Exception as err:
            _LOGGER.error("Unexpected error during group creation: %s", err)
            raise HomeAssistantError(f"Group creation failed: {err}") from err

    async def async_train_group(call: ServiceCall) -> None:
        """Train a person group."""
        person_group_id = call.data[CONF_PERSON_GROUP_ID]
        
        try:
            # Get the Azure Face client
            client = await get_azure_face_client(hass)
            
            # Start training
            await client.train_person_group(person_group_id)
            
            # Monitor training status
            while True:
                status = await client.get_person_group_training_status(person_group_id)
                training_status = status["status"]
                
                if training_status == "succeeded":
                    break
                elif training_status == "failed":
                    error_message = status.get("message", "Training failed")
                    raise HomeAssistantError(f"Training failed: {error_message}")
                
                # Wait before checking again
                await asyncio.sleep(1)
            
            # Fire event with result
            hass.bus.async_fire(
                f"{DOMAIN}_training_result",
                {
                    "person_group_id": person_group_id,
                    "action": "group_trained",
                    "status": "succeeded",
                },
            )
            
            _LOGGER.info("Successfully trained person group %s", person_group_id)
            
        except AzureFaceAPIError as err:
            _LOGGER.error("Azure Face API error during group training: %s", err)
            hass.bus.async_fire(
                f"{DOMAIN}_training_result",
                {
                    "person_group_id": person_group_id,
                    "action": "group_trained",
                    "error": str(err),
                },
            )
            raise HomeAssistantError(f"Azure Face API error: {err}") from err
        
        except Exception as err:
            _LOGGER.error("Unexpected error during group training: %s", err)
            raise HomeAssistantError(f"Group training failed: {err}") from err

    async def async_create_person(call: ServiceCall) -> None:
        """Create a new person in the person group."""
        name = call.data["name"]
        user_data = call.data.get("user_data")
        person_group_id = call.data.get(CONF_PERSON_GROUP_ID)
        
        try:
            # Get the Azure Face client
            client = await get_azure_face_client(hass)
            if not person_group_id:
                person_group_id = await get_person_group_id(hass)
            
            # Create person
            result = await client.create_person(person_group_id, name, user_data)
            person_id = result["personId"]
            
            # Fire event with result
            hass.bus.async_fire(
                f"{DOMAIN}_person_management",
                {
                    "person_group_id": person_group_id,
                    "person_id": person_id,
                    "name": name,
                    "action": "person_created",
                },
            )
            
            _LOGGER.info("Successfully created person %s with ID %s", name, person_id)
            
        except AzureFaceAPIError as err:
            _LOGGER.error("Azure Face API error during person creation: %s", err)
            hass.bus.async_fire(
                f"{DOMAIN}_person_management",
                {
                    "person_group_id": person_group_id,
                    "name": name,
                    "action": "person_created",
                    "error": str(err),
                },
            )
            raise HomeAssistantError(f"Azure Face API error: {err}") from err
        
        except Exception as err:
            _LOGGER.error("Unexpected error during person creation: %s", err)
            raise HomeAssistantError(f"Person creation failed: {err}") from err

    async def async_upload_person_image(call: ServiceCall) -> None:
        """Upload an image for a person with multiple input methods."""
        person_id = call.data["person_id"]
        image_data_b64 = call.data.get("image_data")
        image_path = call.data.get("image_path")
        image_url = call.data.get("image_url")
        detection_model = call.data.get("detection_model", "detection_03")
        person_group_id = call.data.get(CONF_PERSON_GROUP_ID)
        
        if not any([image_data_b64, image_path, image_url]):
            raise HomeAssistantError("Must provide either image_data, image_path, or image_url")
        
        try:
            # Get the Azure Face client
            client = await get_azure_face_client(hass)
            if not person_group_id:
                person_group_id = await get_person_group_id(hass)
            
            # Get image data based on input method
            image_data = None
            
            if image_data_b64:
                # Base64 encoded image data
                try:
                    image_data = base64.b64decode(image_data_b64)
                except Exception as err:
                    raise HomeAssistantError(f"Invalid base64 image data: {err}") from err
                    
            elif image_path:
                # Read image from file path
                try:
                    with open(image_path, "rb") as f:
                        image_data = f.read()
                except Exception as err:
                    raise HomeAssistantError(f"Failed to read image file {image_path}: {err}") from err
                    
            elif image_url:
                # Download image from URL (existing functionality)
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as response:
                        if response.status != 200:
                            raise HomeAssistantError(f"Failed to download image from {image_url}")
                        image_data = await response.read()
            
            # Add face to person
            result = await client.add_person_face(
                person_group_id, person_id, image_data, detection_model
            )
            
            # Fire event with result
            hass.bus.async_fire(
                f"{DOMAIN}_person_management",
                {
                    "person_group_id": person_group_id,
                    "person_id": person_id,
                    "persisted_face_id": result["persistedFaceId"],
                    "action": "image_uploaded",
                },
            )
            
            _LOGGER.info("Successfully uploaded image for person %s", person_id)
            
        except AzureFaceAPIError as err:
            _LOGGER.error("Azure Face API error during image upload: %s", err)
            hass.bus.async_fire(
                f"{DOMAIN}_person_management",
                {
                    "person_group_id": person_group_id,
                    "person_id": person_id,
                    "action": "image_uploaded",
                    "error": str(err),
                },
            )
            raise HomeAssistantError(f"Azure Face API error: {err}") from err
        
        except Exception as err:
            _LOGGER.error("Unexpected error during image upload: %s", err)
            raise HomeAssistantError(f"Image upload failed: {err}") from err

    async def async_get_training_status(call: ServiceCall) -> None:
        """Get the training status of the person group."""
        person_group_id = call.data.get(CONF_PERSON_GROUP_ID)
        
        try:
            # Get the Azure Face client
            client = await get_azure_face_client(hass)
            if not person_group_id:
                person_group_id = await get_person_group_id(hass)
            
            # Get training status
            status = await client.get_person_group_training_status(person_group_id)
            
            # Fire event with result
            hass.bus.async_fire(
                f"{DOMAIN}_training_status",
                {
                    "person_group_id": person_group_id,
                    "status": status["status"],
                    "created_time": status.get("createdTime"),
                    "last_action_time": status.get("lastActionTime"),
                    "last_successful_training_time": status.get("lastSuccessfulTrainingTime"),
                    "message": status.get("message"),
                },
            )
            
            _LOGGER.info("Training status for group %s: %s", person_group_id, status["status"])
            
        except AzureFaceAPIError as err:
            _LOGGER.error("Azure Face API error getting training status: %s", err)
            hass.bus.async_fire(
                f"{DOMAIN}_training_status",
                {
                    "person_group_id": person_group_id,
                    "error": str(err),
                },
            )
            raise HomeAssistantError(f"Azure Face API error: {err}") from err
        
        except Exception as err:
            _LOGGER.error("Unexpected error getting training status: %s", err)
            raise HomeAssistantError(f"Getting training status failed: {err}") from err

    async def async_list_persons(call: ServiceCall) -> None:
        """List all persons in the person group."""
        person_group_id = call.data.get(CONF_PERSON_GROUP_ID)
        
        try:
            # Get the Azure Face client
            client = await get_azure_face_client(hass)
            if not person_group_id:
                person_group_id = await get_person_group_id(hass)
            
            # List persons
            persons = await client.list_persons(person_group_id)
            
            # Fire event with result
            hass.bus.async_fire(
                f"{DOMAIN}_persons_list",
                {
                    "person_group_id": person_group_id,
                    "persons": persons,
                },
            )
            
            _LOGGER.info("Listed %d persons in group %s", len(persons), person_group_id)
            
        except AzureFaceAPIError as err:
            _LOGGER.error("Azure Face API error listing persons: %s", err)
            hass.bus.async_fire(
                f"{DOMAIN}_persons_list",
                {
                    "person_group_id": person_group_id,
                    "error": str(err),
                },
            )
            raise HomeAssistantError(f"Azure Face API error: {err}") from err
        
        except Exception as err:
            _LOGGER.error("Unexpected error listing persons: %s", err)
            raise HomeAssistantError(f"Listing persons failed: {err}") from err

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_RECOGNIZE_FACE,
        async_recognize_face,
        schema=SERVICE_RECOGNIZE_FACE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_TRAIN_PERSON,
        async_train_person,
        schema=SERVICE_TRAIN_PERSON_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_PERSON_GROUP,
        async_create_person_group,
        schema=SERVICE_CREATE_PERSON_GROUP_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_TRAIN_GROUP,
        async_train_group,
        schema=SERVICE_TRAIN_GROUP_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_PERSON,
        async_create_person,
        schema=SERVICE_CREATE_PERSON_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_UPLOAD_PERSON_IMAGE,
        async_upload_person_image,
        schema=SERVICE_UPLOAD_PERSON_IMAGE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_TRAINING_STATUS,
        async_get_training_status,
        schema=SERVICE_GET_TRAINING_STATUS_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_LIST_PERSONS,
        async_list_persons,
        schema=SERVICE_LIST_PERSONS_SCHEMA,
    )