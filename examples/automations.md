# Azure Face Recognition - Example Automations

This directory contains example automations and configurations for the Azure Face Recognition integration.

## Face Recognition Automation

### Basic Face Recognition on Motion
```yaml
automation:
  - alias: "Face Recognition on Front Door Motion"
    trigger:
      - platform: state
        entity_id: binary_sensor.front_door_motion
        to: "on"
    action:
      - service: azure_face.recognize_face
        data:
          camera_entity: camera.front_door
          confidence_threshold: 0.8
```

### Advanced Recognition with Notifications
```yaml
automation:
  - alias: "Face Recognition with Smart Notifications"
    trigger:
      - platform: event
        event_type: azure_face_recognition_result
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.faces_detected > 0 }}"
    action:
      - choose:
          - conditions:
              - condition: template
                value_template: "{{ trigger.event.data.identifications | length > 0 }}"
            sequence:
              - service: notify.mobile_app
                data:
                  title: "Known Person Detected"
                  message: >
                    {{ trigger.event.data.identifications[0].candidates[0].person_id }}
                    detected at {{ trigger.event.data.camera_entity }}
                    (Confidence: {{ (trigger.event.data.identifications[0].candidates[0].confidence * 100) | round(1) }}%)
          - conditions:
              - condition: template
                value_template: "{{ trigger.event.data.identifications | length == 0 }}"
            sequence:
              - service: notify.mobile_app
                data:
                  title: "Unknown Person Detected"
                  message: >
                    Unknown person detected at {{ trigger.event.data.camera_entity }}
```

## Training Automations

### Scheduled Training
```yaml
automation:
  - alias: "Weekly Person Group Training"
    trigger:
      - platform: time
        at: "02:00:00"
      - platform: time
        at: "14:00:00"
    condition:
      - condition: time
        weekday:
          - sun
    action:
      - service: azure_face.train_group
        data:
          person_group_id: "family_members"
```

### Training from File Uploads
```yaml
automation:
  - alias: "Train Person from File Upload"
    trigger:
      - platform: webhook
        webhook_id: azure_face_training
    action:
      - service: azure_face.train_person
        data:
          person_id: "{{ trigger.json.person_id }}"
          image_url: "{{ trigger.json.image_url }}"
```

## Dashboard Configuration

### Lovelace Card for Face Recognition
```yaml
type: vertical-stack
cards:
  - type: picture-entity
    entity: camera.front_door
    name: Front Door Camera
  - type: button
    name: Recognize Faces
    tap_action:
      action: call-service
      service: azure_face.recognize_face
      service_data:
        camera_entity: camera.front_door
        confidence_threshold: 0.7
  - type: entities
    entities:
      - sensor.last_face_recognition_result
      - sensor.last_recognized_person
```

## Helper Sensors

### Template Sensors for Results
```yaml
template:
  - sensor:
      - name: "Last Face Recognition Result"
        state: >
          {% set event = state_attr('sensor.last_azure_face_event', 'event_data') %}
          {% if event and event.faces_detected > 0 %}
            {% if event.identifications | length > 0 %}
              Known Person
            {% else %}
              Unknown Person
            {% endif %}
          {% else %}
            No Face Detected
          {% endif %}
        attributes:
          faces_detected: >
            {% set event = state_attr('sensor.last_azure_face_event', 'event_data') %}
            {{ event.faces_detected if event else 0 }}
          camera: >
            {% set event = state_attr('sensor.last_azure_face_event', 'event_data') %}
            {{ event.camera_entity if event else 'none' }}

  - sensor:
      - name: "Last Recognized Person"
        state: >
          {% set event = state_attr('sensor.last_azure_face_event', 'event_data') %}
          {% if event and event.identifications | length > 0 %}
            {{ event.identifications[0].candidates[0].person_id }}
          {% else %}
            Unknown
          {% endif %}
        attributes:
          confidence: >
            {% set event = state_attr('sensor.last_azure_face_event', 'event_data') %}
            {% if event and event.identifications | length > 0 %}
              {{ (event.identifications[0].candidates[0].confidence * 100) | round(1) }}%
            {% else %}
              0%
            {% endif %}
```

## Scripts

### Manual Recognition Script
```yaml
script:
  recognize_front_door:
    alias: "Recognize Face at Front Door"
    sequence:
      - service: azure_face.recognize_face
        data:
          camera_entity: camera.front_door
          confidence_threshold: 0.8
      - wait_for_trigger:
          - platform: event
            event_type: azure_face_recognition_result
        timeout: 30
      - service: persistent_notification.create
        data:
          title: "Face Recognition Complete"
          message: >
            {% if wait.trigger.event.data.faces_detected > 0 %}
              {% if wait.trigger.event.data.identifications | length > 0 %}
                Identified: {{ wait.trigger.event.data.identifications[0].candidates[0].person_id }}
              {% else %}
                Unknown person detected
              {% endif %}
            {% else %}
              No faces detected
            {% endif %}
```

### Bulk Training Script
```yaml
script:
  train_family_members:
    alias: "Train Family Members"
    sequence:
      - service: azure_face.train_person
        data:
          person_id: "john_doe"
          image_url: "https://example.com/photos/john1.jpg"
      - delay: 2
      - service: azure_face.train_person
        data:
          person_id: "john_doe"
          image_url: "https://example.com/photos/john2.jpg"
      - delay: 2
      - service: azure_face.train_person
        data:
          person_id: "jane_doe"
          image_url: "https://example.com/photos/jane1.jpg"
      - delay: 2
      - service: azure_face.train_group
        data:
          person_group_id: "family_members"
```