# Azure Face Recognition for Home Assistant

A comprehensive Home Assistant custom integration for Azure AI facial recognition that provides face detection, identification, and training capabilities through Azure Cognitive Services Face API.

## Features

- **Easy Configuration**: UI-based setup wizard with support for multiple Azure regions
- **Face Recognition**: Analyze camera images for face detection and identification
- **Training System**: Add and manage training images for people
- **Person Group Management**: Create and organize person groups
- **Person Management GUI**: Comprehensive web interface for managing people and training
- **Camera Integration**: Direct integration with Home Assistant camera entities
- **Event-Driven**: Publishes recognition results as Home Assistant events
- **HACS Compatible**: Easy installation through HACS

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/loryanstrant/ha-azureface`
6. Select "Integration" as the category
7. Click "Add"
8. Find "Azure Face Recognition" in the integration list and install it
9. Restart Home Assistant

### Manual Installation

1. Download the `azure_face` folder from this repository
2. Copy it to your Home Assistant `custom_components` directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings** > **Devices & Services**
2. Click **Add Integration**
3. Search for "Azure Face Recognition"
4. Follow the configuration wizard:
   - Select your Azure region or enter a custom endpoint
   - Enter your Azure Face API key
   - Choose to create a new person group or select an existing one

## Person Management GUI

After configuration, access the person management interface through the Home Assistant sidebar:

1. Look for the **Azure Face** panel in the sidebar
2. Use the interface to:
   - **Create New People**: Add people to your person group
   - **Upload Images**: Add training images for better recognition
   - **Manage Training**: Start training and monitor status
   - **View People**: List all people in your person group

## Services

### `azure_face.recognize_face`

Analyze a camera image for face recognition.

**Parameters:**
- `camera_entity` (required): Camera entity to capture image from
- `confidence_threshold` (optional): Minimum confidence for identification (0.0-1.0, default: 0.7)

**Example:**
```yaml
service: azure_face.recognize_face
data:
  camera_entity: camera.front_door
  confidence_threshold: 0.8
```

### `azure_face.create_person`

Create a new person in the person group.

**Parameters:**
- `name` (required): Name of the person
- `user_data` (optional): Additional user-defined data
- `person_group_id` (optional): Person group ID (uses default if not specified)

**Example:**
```yaml
service: azure_face.create_person
data:
  name: "John Doe"
  user_data: "Employee ID: 12345"
```

### `azure_face.upload_person_image`

Upload an image for a person with multiple input methods.

**Parameters:**
- `person_id` (required): Unique identifier of the person
- `image_data` (optional): Base64 encoded image data
- `image_path` (optional): Path to image file on the system
- `image_url` (optional): URL of the image to upload
- `detection_model` (optional): Detection model to use (default: "detection_03")
- `person_group_id` (optional): Person group ID (uses default if not specified)

**Examples:**
```yaml
# Upload from file path
service: azure_face.upload_person_image
data:
  person_id: "abc123-def456"
  image_path: "/config/images/john_doe.jpg"

# Upload from URL
service: azure_face.upload_person_image
data:
  person_id: "abc123-def456"
  image_url: "https://example.com/photo.jpg"

# Upload base64 data
service: azure_face.upload_person_image
data:
  person_id: "abc123-def456"
  image_data: "iVBORw0KGgoAAAANSUhEUgAA..."
```

### `azure_face.get_training_status`

Get the current training status of the person group.

**Parameters:**
- `person_group_id` (optional): Person group to check (uses default if not specified)

**Example:**
```yaml
service: azure_face.get_training_status
```

### `azure_face.list_persons`

List all persons in the person group.

**Parameters:**
- `person_group_id` (optional): Person group to list from (uses default if not specified)

**Example:**
```yaml
service: azure_face.list_persons
```

### `azure_face.create_person_group`

Create a new person group.

**Parameters:**
- `person_group_id` (required): Unique identifier for the group
- `name` (required): Display name for the group
- `user_data` (optional): Additional user-defined data
- `recognition_model` (optional): Recognition model to use (default: "recognition_04")

### `azure_face.train_group`

Train a person group to enable identification.

**Parameters:**
- `person_group_id` (required): The person group to train

## Events

The integration publishes the following events:

### `azure_face_recognition_result`

Fired when face recognition is completed.

**Event Data:**
- `camera_entity`: The camera that was analyzed
- `faces_detected`: Number of faces found
- `identifications`: Array of recognition results
- `error`: Error message if recognition failed

### `azure_face_training_result`

Fired when training operations are completed.

### `azure_face_group_management`

Fired when person group operations are completed.

### `azure_face_person_management`

Fired when person management operations are completed.

**Event Data:**
- `person_group_id`: The person group ID
- `person_id`: The person ID (for person-specific operations)
- `action`: The action performed (person_created, image_uploaded)
- `error`: Error message if operation failed

### `azure_face_training_status`

Fired when training status is requested.

**Event Data:**
- `person_group_id`: The person group ID
- `status`: Current training status (running, succeeded, failed)
- `created_time`: When training was created
- `last_action_time`: Last action timestamp
- `message`: Additional status message

### `azure_face_persons_list`

Fired when persons list is requested.

**Event Data:**
- `person_group_id`: The person group ID
- `persons`: Array of person objects
- `error`: Error message if operation failed

## Requirements

- Home Assistant 2023.1 or later
- Azure Cognitive Services Face API subscription
- Valid Azure Face API key and endpoint

## Azure Setup

1. Create an Azure account at [portal.azure.com](https://portal.azure.com)
2. Create a Cognitive Services resource
3. Select the Face API service
4. Note your API key and endpoint URL
5. Use these credentials in the Home Assistant configuration

## Troubleshooting

### Connection Issues
- Verify your API key is correct and active
- Check that your endpoint URL is valid
- Ensure your Home Assistant instance can reach the Azure endpoints

### Recognition Issues
- Ensure your person group is trained after adding people
- Check that images meet Azure Face API requirements (good lighting, clear face visibility)
- Adjust confidence threshold if getting too many or too few matches

### Image Requirements
- Supported formats: JPEG, PNG, BMP, GIF
- Maximum file size: 6MB
- Image dimensions: between 36x36 and 4096x4096 pixels

## Support

For issues and feature requests, please use the [GitHub issue tracker](https://github.com/loryanstrant/ha-azureface/issues).
