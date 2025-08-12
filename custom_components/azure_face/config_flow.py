"""Config flow for Azure Face integration."""
import logging
from typing import Any, Dict, Optional
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import DOMAIN, CONF_API_KEY, CONF_ENDPOINT, CONF_PERSON_GROUP_ID, AZURE_REGIONS
from .azure_client import AzureFaceClient, AzureFaceAPIError

_LOGGER = logging.getLogger(__name__)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


async def validate_input(hass: HomeAssistant, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    api_key = data[CONF_API_KEY]
    endpoint = data[CONF_ENDPOINT]

    client = AzureFaceClient(hass, endpoint, api_key)

    try:
        # Test the connection
        if not await client.test_connection():
            raise InvalidAuth
    except AzureFaceAPIError as err:
        if "authentication" in str(err).lower():
            raise InvalidAuth from err
        raise CannotConnect from err

    # Return info that you want to store in the config entry.
    return {"title": f"Azure Face ({endpoint.split('//')[1].split('.')[0].title()})"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Azure Face."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._data = {}

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            # Handle region selection and endpoint
            region = user_input.get("region")
            if region == "custom":
                endpoint = user_input.get(CONF_ENDPOINT)
                if not endpoint:
                    errors["base"] = "missing_custom_endpoint"
                    return self.async_show_form(
                        step_id="user", data_schema=data_schema, errors=errors
                    )
            else:
                endpoint = AZURE_REGIONS.get(region)
                if not endpoint:
                    errors["base"] = "invalid_region"
                    return self.async_show_form(
                        step_id="user", data_schema=data_schema, errors=errors
                    )
            
            # Create validation data with the correct endpoint
            validation_data = {
                CONF_API_KEY: user_input[CONF_API_KEY],
                CONF_ENDPOINT: endpoint,
            }
            
            try:
                info = await validate_input(self.hass, validation_data)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Store the data for the next step
                self._data.update(user_input)
                self._data[CONF_ENDPOINT] = endpoint
                return await self.async_step_person_group()

        # Build the schema for region selection
        region_options = [
            {"value": region, "label": f"{region.title()} ({endpoint})"}
            for region, endpoint in AZURE_REGIONS.items()
        ]
        region_options.append({"value": "custom", "label": "Custom endpoint"})

        data_schema = vol.Schema({
            vol.Required("region", default="eastus"): SelectSelector(
                SelectSelectorConfig(options=region_options)
            ),
            vol.Optional(CONF_ENDPOINT): TextSelector(
                TextSelectorConfig(type=TextSelectorType.URL)
            ),
            vol.Required(CONF_API_KEY): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)
            ),
        })

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def async_step_person_group(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the person group step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            self._data.update(user_input)
            
            # If creating a new person group, validate the ID
            if user_input.get("create_new_group"):
                person_group_id = user_input.get(CONF_PERSON_GROUP_ID + "_manual")
                group_name = user_input.get("group_name")
                
                if not person_group_id:
                    errors["base"] = "missing_person_group_id"
                elif not person_group_id.replace("_", "").replace("-", "").isalnum():
                    errors["base"] = "invalid_person_group_id"
                elif not group_name:
                    errors["base"] = "missing_group_name"
                else:
                    # Try to create the person group
                    try:
                        endpoint = self._data.get(CONF_ENDPOINT)
                        if self._data.get("region") != "custom":
                            endpoint = AZURE_REGIONS[self._data["region"]]
                            
                        client = AzureFaceClient(
                            self.hass, endpoint, self._data[CONF_API_KEY]
                        )
                        await client.create_person_group(
                            person_group_id,
                            group_name,
                            user_input.get("group_description"),
                        )
                        self._data[CONF_PERSON_GROUP_ID] = person_group_id
                        self._data[CONF_ENDPOINT] = endpoint
                    except AzureFaceAPIError as err:
                        _LOGGER.error("Failed to create person group: %s", err)
                        errors["base"] = "cannot_create_group"
            else:
                # Using existing person group
                person_group_id = user_input.get(CONF_PERSON_GROUP_ID)
                if not person_group_id:
                    errors["base"] = "missing_person_group_id"
                else:
                    self._data[CONF_PERSON_GROUP_ID] = person_group_id
                    endpoint = self._data.get(CONF_ENDPOINT)
                    if self._data.get("region") != "custom":
                        endpoint = AZURE_REGIONS[self._data["region"]]
                    self._data[CONF_ENDPOINT] = endpoint

            if not errors:
                return self.async_create_entry(
                    title=f"Azure Face ({self._data[CONF_PERSON_GROUP_ID]})",
                    data=self._data,
                )

        # Get existing person groups to offer as options
        person_group_options = []
        try:
            endpoint = self._data.get(CONF_ENDPOINT)
            if self._data.get("region") != "custom":
                endpoint = AZURE_REGIONS[self._data["region"]]
                
            client = AzureFaceClient(self.hass, endpoint, self._data[CONF_API_KEY])
            groups = await client.list_person_groups()
            person_group_options = [
                {"value": group["personGroupId"], "label": f"{group['name']} ({group['personGroupId']})"}
                for group in groups
            ]
        except Exception as err:
            _LOGGER.warning("Could not fetch existing person groups: %s", err)

        data_schema = vol.Schema({
            vol.Optional("create_new_group", default=True): bool,
        })

        if person_group_options:
            data_schema = data_schema.extend({
                vol.Optional(CONF_PERSON_GROUP_ID): SelectSelector(
                    SelectSelectorConfig(options=person_group_options)
                ),
            })

        data_schema = data_schema.extend({
            vol.Optional("group_name"): TextSelector(),
            vol.Optional("group_description"): TextSelector(
                TextSelectorConfig(multiline=True)
            ),
            vol.Optional(CONF_PERSON_GROUP_ID + "_manual"): TextSelector(),
        })

        return self.async_show_form(
            step_id="person_group", data_schema=data_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Azure Face config flow options handler."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema({
            vol.Optional(
                "confidence_threshold",
                default=self.config_entry.options.get("confidence_threshold", 0.7),
            ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0)),
            vol.Optional(
                "detection_model",
                default=self.config_entry.options.get("detection_model", "detection_03"),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[
                        {"value": "detection_01", "label": "Detection 01"},
                        {"value": "detection_02", "label": "Detection 02"},
                        {"value": "detection_03", "label": "Detection 03 (recommended)"},
                    ]
                )
            ),
            vol.Optional(
                "recognition_model",
                default=self.config_entry.options.get("recognition_model", "recognition_04"),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[
                        {"value": "recognition_01", "label": "Recognition 01"},
                        {"value": "recognition_02", "label": "Recognition 02"},
                        {"value": "recognition_03", "label": "Recognition 03"},
                        {"value": "recognition_04", "label": "Recognition 04 (recommended)"},
                    ]
                )
            ),
        })

        return self.async_show_form(
            step_id="init", data_schema=data_schema
        )