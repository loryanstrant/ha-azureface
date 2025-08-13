"""Azure Face API client for Home Assistant integration."""
import asyncio
import logging
import aiohttp
import json
from typing import Any, Dict, List, Optional, Union
from PIL import Image
import io
import base64

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.core import HomeAssistant

from .const import (
    DEFAULT_TIMEOUT,
    MAX_IMAGE_SIZE,
    SUPPORTED_IMAGE_FORMATS,
    ERROR_INVALID_IMAGE,
    ERROR_NO_FACE_DETECTED,
    ERROR_API_ERROR,
    ERROR_QUOTA_EXCEEDED,
    ERROR_AUTHENTICATION_FAILED,
)

_LOGGER = logging.getLogger(__name__)


class AzureFaceAPIError(Exception):
    """Exception raised for Azure Face API errors."""

    def __init__(self, message: str, error_code: str = ERROR_API_ERROR):
        super().__init__(message)
        self.error_code = error_code


class AzureFaceClient:
    """Client for Azure Face API."""

    def __init__(self, hass: HomeAssistant, endpoint: str, api_key: str):
        """Initialize the Azure Face client."""
        self.hass = hass
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.session = async_get_clientsession(hass)

    async def _make_request(
        self,
        method: str,
        url: str,
        data: Optional[Union[bytes, Dict[str, Any]]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make a request to the Azure Face API."""
        default_headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
        }
        
        if headers:
            default_headers.update(headers)

        if isinstance(data, dict):
            default_headers["Content-Type"] = "application/json"
            data = json.dumps(data).encode("utf-8")
        elif isinstance(data, bytes):
            default_headers["Content-Type"] = "application/octet-stream"

        try:
            async with self.session.request(
                method,
                url,
                data=data,
                params=params,
                headers=default_headers,
                timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT),
            ) as response:
                response_text = await response.text()
                
                if response.status == 401:
                    raise AzureFaceAPIError(
                        "Authentication failed. Please check your API key.",
                        ERROR_AUTHENTICATION_FAILED
                    )
                elif response.status == 429:
                    raise AzureFaceAPIError(
                        "API quota exceeded. Please wait before retrying.",
                        ERROR_QUOTA_EXCEEDED
                    )
                elif response.status >= 400:
                    try:
                        error_data = json.loads(response_text)
                        error_message = error_data.get("error", {}).get("message", response_text)
                    except json.JSONDecodeError:
                        error_message = response_text
                    
                    _LOGGER.error("Azure Face API error: %s (status: %s)", error_message, response.status)
                    raise AzureFaceAPIError(f"API error: {error_message}")

                if response_text:
                    return json.loads(response_text)
                return {}

        except aiohttp.ClientError as err:
            _LOGGER.error("Network error calling Azure Face API: %s", err)
            raise AzureFaceAPIError(f"Network error: {err}")

    async def detect_faces(self, image_data: bytes, detection_model: str = "detection_03") -> List[Dict[str, Any]]:
        """Detect faces in an image."""
        url = f"{self.endpoint}/face/v1.0/detect"
        
        params = {
            "detectionModel": detection_model,
            "returnFaceId": True,
            "returnFaceLandmarks": False,
            "returnFaceAttributes": "age,gender,emotion,facialHair,glasses,smile,makeup,accessories,blur,exposure,noise",
        }

        # Validate image
        await self._validate_image(image_data)
        
        response = await self._make_request("POST", url, data=image_data, params=params)
        return response

    async def identify_faces(
        self,
        face_ids: List[str],
        person_group_id: str,
        max_candidates: int = 1,
        confidence_threshold: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """Identify faces using a person group."""
        url = f"{self.endpoint}/face/v1.0/identify"
        
        data = {
            "faceIds": face_ids,
            "personGroupId": person_group_id,
            "maxNumOfCandidatesReturned": max_candidates,
            "confidenceThreshold": confidence_threshold,
        }

        response = await self._make_request("POST", url, data=data)
        return response

    async def create_person_group(
        self,
        person_group_id: str,
        name: str,
        user_data: Optional[str] = None,
        recognition_model: str = "recognition_04",
    ) -> None:
        """Create a person group."""
        url = f"{self.endpoint}/face/v1.0/persongroups/{person_group_id}"
        
        data = {
            "name": name,
            "recognitionModel": recognition_model,
        }
        
        if user_data:
            data["userData"] = user_data

        await self._make_request("PUT", url, data=data)

    async def train_person_group(self, person_group_id: str) -> None:
        """Train a person group."""
        url = f"{self.endpoint}/face/v1.0/persongroups/{person_group_id}/train"
        await self._make_request("POST", url)

    async def get_person_group_training_status(self, person_group_id: str) -> Dict[str, Any]:
        """Get the training status of a person group."""
        url = f"{self.endpoint}/face/v1.0/persongroups/{person_group_id}/training"
        return await self._make_request("GET", url)

    async def create_person(self, person_group_id: str, name: str, user_data: Optional[str] = None) -> Dict[str, Any]:
        """Create a person in a person group."""
        url = f"{self.endpoint}/face/v1.0/persongroups/{person_group_id}/persons"
        
        data = {
            "name": name,
        }
        
        if user_data:
            data["userData"] = user_data

        return await self._make_request("POST", url, data=data)

    async def add_person_face(
        self,
        person_group_id: str,
        person_id: str,
        image_data: bytes,
        detection_model: str = "detection_03",
    ) -> Dict[str, Any]:
        """Add a face to a person."""
        url = f"{self.endpoint}/face/v1.0/persongroups/{person_group_id}/persons/{person_id}/persistedFaces"
        
        params = {
            "detectionModel": detection_model,
        }

        # Validate image
        await self._validate_image(image_data)
        
        return await self._make_request("POST", url, data=image_data, params=params)

    async def list_person_groups(self) -> List[Dict[str, Any]]:
        """List all person groups."""
        url = f"{self.endpoint}/face/v1.0/persongroups"
        return await self._make_request("GET", url)

    async def get_person_group(self, person_group_id: str) -> Dict[str, Any]:
        """Get a person group."""
        url = f"{self.endpoint}/face/v1.0/persongroups/{person_group_id}"
        return await self._make_request("GET", url)

    async def list_persons(self, person_group_id: str) -> List[Dict[str, Any]]:
        """List persons in a person group."""
        url = f"{self.endpoint}/face/v1.0/persongroups/{person_group_id}/persons"
        return await self._make_request("GET", url)

    async def get_person(self, person_group_id: str, person_id: str) -> Dict[str, Any]:
        """Get a specific person from a person group."""
        url = f"{self.endpoint}/face/v1.0/persongroups/{person_group_id}/persons/{person_id}"
        return await self._make_request("GET", url)

    async def _validate_image(self, image_data: bytes) -> None:
        """Validate image data."""
        if len(image_data) > MAX_IMAGE_SIZE:
            raise AzureFaceAPIError(
                f"Image size exceeds maximum of {MAX_IMAGE_SIZE / (1024 * 1024):.1f}MB",
                ERROR_INVALID_IMAGE
            )

        try:
            # Validate image format using PIL
            image = Image.open(io.BytesIO(image_data))
            image.verify()
            
            # Check if image format is supported
            mime_type = f"image/{image.format.lower()}"
            if mime_type not in SUPPORTED_IMAGE_FORMATS:
                raise AzureFaceAPIError(
                    f"Unsupported image format: {image.format}. Supported formats: JPEG, PNG, BMP, GIF",
                    ERROR_INVALID_IMAGE
                )
                
        except Exception as err:
            _LOGGER.error("Image validation failed: %s", err)
            raise AzureFaceAPIError(
                "Invalid image format or corrupted image",
                ERROR_INVALID_IMAGE
            ) from err

    async def test_connection(self) -> bool:
        """Test the connection to Azure Face API."""
        try:
            await self.list_person_groups()
            return True
        except AzureFaceAPIError:
            return False