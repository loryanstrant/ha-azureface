# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-08-12

### Added
- Initial release of Azure Face Recognition integration
- Complete configuration UI wizard with Azure region selection
- Face recognition service for camera image analysis
- Person training functionality with image URL support
- Person group creation and management
- Person group training capabilities
- Event-driven architecture for recognition results
- Comprehensive error handling and validation
- Support for multiple Azure Face API detection and recognition models
- HACS compliance with proper manifest and file structure
- Secure credential storage through Home Assistant's configuration system
- Rate limiting and async operations for optimal performance
- Multi-language support (English included)
- Comprehensive documentation and examples

### Features
- **Configuration Flow**: Easy setup wizard with region selection and person group management
- **Face Recognition**: Analyze camera images for face detection and identification
- **Training System**: Add training images for people via URL
- **Camera Integration**: Direct integration with Home Assistant camera entities
- **Event Publishing**: Recognition results published as Home Assistant events
- **Options Flow**: Advanced configuration options for detection and recognition models
- **Error Handling**: Comprehensive error handling with user-friendly messages
- **Azure Integration**: Full support for Azure Face API with multiple regions

### Services
- `azure_face.recognize_face`: Analyze camera image for face recognition
- `azure_face.train_person`: Add training images for a person
- `azure_face.create_person_group`: Create new person groups
- `azure_face.train_group`: Train the person group model

### Events
- `azure_face_recognition_result`: Face recognition results
- `azure_face_training_result`: Training operation results
- `azure_face_group_management`: Person group management results