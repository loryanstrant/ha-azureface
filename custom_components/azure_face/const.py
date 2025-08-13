"""Constants for the Azure Face integration."""
import voluptuous as vol
from homeassistant.helpers import config_validation as cv

DOMAIN = "azure_face"

# Configuration keys
CONF_API_KEY = "api_key"
CONF_ENDPOINT = "endpoint"
CONF_PERSON_GROUP_ID = "person_group_id"
CONF_CAMERA_ENTITY = "camera_entity"

# Service names
SERVICE_RECOGNIZE_FACE = "recognize_face"
SERVICE_TRAIN_PERSON = "train_person"
SERVICE_CREATE_PERSON_GROUP = "create_person_group"
SERVICE_TRAIN_GROUP = "train_group"
SERVICE_CREATE_PERSON = "create_person"
SERVICE_UPLOAD_PERSON_IMAGE = "upload_person_image"
SERVICE_GET_TRAINING_STATUS = "get_training_status"
SERVICE_LIST_PERSONS = "list_persons"

# Default values
DEFAULT_TIMEOUT = 10
DEFAULT_CONFIDENCE_THRESHOLD = 0.7
MAX_IMAGE_SIZE = 6 * 1024 * 1024  # 6MB
SUPPORTED_IMAGE_FORMATS = ["image/jpeg", "image/png", "image/bmp", "image/gif"]

# Azure Face API endpoints
AZURE_REGIONS = {
    "eastus": "https://eastus.api.cognitive.microsoft.com",
    "eastus2": "https://eastus2.api.cognitive.microsoft.com",
    "westus": "https://westus.api.cognitive.microsoft.com",
    "westus2": "https://westus2.api.cognitive.microsoft.com",
    "westeurope": "https://westeurope.api.cognitive.microsoft.com",
    "northeurope": "https://northeurope.api.cognitive.microsoft.com",
    "southeastasia": "https://southeastasia.api.cognitive.microsoft.com",
    "eastasia": "https://eastasia.api.cognitive.microsoft.com",
}

# Service schemas
SERVICE_RECOGNIZE_FACE_SCHEMA = vol.Schema({
    vol.Required(CONF_CAMERA_ENTITY): cv.entity_id,
    vol.Optional("confidence_threshold", default=DEFAULT_CONFIDENCE_THRESHOLD): vol.All(
        vol.Coerce(float), vol.Range(min=0.0, max=1.0)
    ),
})

SERVICE_TRAIN_PERSON_SCHEMA = vol.Schema({
    vol.Required("person_id"): cv.string,
    vol.Required("image_url"): cv.url,
    vol.Optional("detection_model", default="detection_03"): cv.string,
})

SERVICE_CREATE_PERSON_GROUP_SCHEMA = vol.Schema({
    vol.Required(CONF_PERSON_GROUP_ID): cv.string,
    vol.Required("name"): cv.string,
    vol.Optional("user_data"): cv.string,
    vol.Optional("recognition_model", default="recognition_04"): cv.string,
})

SERVICE_TRAIN_GROUP_SCHEMA = vol.Schema({
    vol.Required(CONF_PERSON_GROUP_ID): cv.string,
})

SERVICE_CREATE_PERSON_SCHEMA = vol.Schema({
    vol.Required("name"): cv.string,
    vol.Optional("user_data"): cv.string,
    vol.Optional(CONF_PERSON_GROUP_ID): cv.string,
})

SERVICE_UPLOAD_PERSON_IMAGE_SCHEMA = vol.Schema({
    vol.Required("person_id"): cv.string,
    vol.Optional("image_data"): cv.string,  # Base64 encoded image
    vol.Optional("image_path"): cv.string,  # File path
    vol.Optional("image_url"): cv.url,      # URL (existing functionality)
    vol.Optional("detection_model", default="detection_03"): cv.string,
    vol.Optional(CONF_PERSON_GROUP_ID): cv.string,
})

SERVICE_GET_TRAINING_STATUS_SCHEMA = vol.Schema({
    vol.Optional(CONF_PERSON_GROUP_ID): cv.string,
})

SERVICE_LIST_PERSONS_SCHEMA = vol.Schema({
    vol.Optional(CONF_PERSON_GROUP_ID): cv.string,
})

# Error codes
ERROR_INVALID_IMAGE = "invalid_image"
ERROR_NO_FACE_DETECTED = "no_face_detected"
ERROR_MULTIPLE_FACES = "multiple_faces"
ERROR_API_ERROR = "api_error"
ERROR_PERSON_GROUP_NOT_FOUND = "person_group_not_found"
ERROR_QUOTA_EXCEEDED = "quota_exceeded"
ERROR_AUTHENTICATION_FAILED = "authentication_failed"