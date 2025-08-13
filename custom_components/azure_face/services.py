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
    SERVICE_RECOGNIZE_FACE_SCHEMA,
    SERVICE_TRAIN_PERSON_SCHEMA,
    SERVICE_CREATE_PERSON_GROUP_SCHEMA,
    SERVICE_TRAIN_GROUP_SCHEMA,
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