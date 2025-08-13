"""The Azure Face integration."""
import logging
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.typing import ConfigType

from .azure_client import AzureFaceClient, AzureFaceAPIError
from .const import DOMAIN, CONF_API_KEY, CONF_ENDPOINT, CONF_PERSON_GROUP_ID
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = []


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Azure Face integration."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Azure Face from a config entry."""
    api_key = entry.data[CONF_API_KEY]
    endpoint = entry.data[CONF_ENDPOINT]
    person_group_id = entry.data[CONF_PERSON_GROUP_ID]

    # Create the Azure Face client
    client = AzureFaceClient(hass, endpoint, api_key)

    # Test the connection
    try:
        if not await client.test_connection():
            raise ConfigEntryNotReady("Unable to connect to Azure Face API")
    except AzureFaceAPIError as err:
        _LOGGER.error("Failed to connect to Azure Face API: %s", err)
        raise ConfigEntryNotReady("Unable to connect to Azure Face API") from err

    # Store the client and configuration
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "person_group_id": person_group_id,
        "config": entry,
    }

    # Set up services
    await async_setup_services(hass)

    # Register the person management panel
    await async_register_panel(hass)

    # Set up platforms if any are defined
    if PLATFORMS:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_register_panel(hass: HomeAssistant) -> None:
    """Register the person management panel."""
    # Register the static files
    await hass.http.async_register_static_paths([
        {
            "path": f"/{DOMAIN}",
            "file_path": hass.config.path(f"custom_components/{DOMAIN}/www"),
            "cache_headers": True,
        }
    ])
    
    # Register the panel using the most compatible approach
    try:
        # This is the modern approach for Home Assistant 2023.x+
        from homeassistant.helpers import panel_iframe
        await panel_iframe.async_register_panel(
            hass,
            DOMAIN,
            "Azure Face",
            "mdi:face-recognition",
            f"/{DOMAIN}/person-management.html",
            require_admin=True,
        )
    except (ImportError, AttributeError):
        # Fallback for older Home Assistant versions
        _LOGGER.warning("Could not register panel using panel_iframe helper, trying fallback method")
        try:
            # Use the standard frontend panel registration
            hass.components.frontend.async_register_built_in_panel(
                "iframe",
                "Azure Face",
                "mdi:face-recognition",
                DOMAIN,
                {"url": f"/{DOMAIN}/person-management.html"},
                require_admin=True,
            )
        except Exception as ex:
            _LOGGER.warning("Unable to register Azure Face panel: %s", ex)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms if any are defined
    if PLATFORMS:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        if not unload_ok:
            return False

    # Remove the entry from hass.data
    hass.data[DOMAIN].pop(entry.entry_id)

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


# Helper functions are now in helpers.py to avoid circular imports
from .helpers import get_azure_face_client, get_person_group_id