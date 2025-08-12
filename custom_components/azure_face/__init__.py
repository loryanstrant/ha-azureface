"""The Azure Face integration."""
import asyncio
import logging
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.typing import ConfigType

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

    # Set up platforms if any are defined
    if PLATFORMS:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


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


async def get_azure_face_client(hass: HomeAssistant, entry_id: str = None) -> AzureFaceClient:
    """Get Azure Face client from the first available entry or specified entry."""
    if not hass.data.get(DOMAIN):
        raise ValueError("Azure Face integration not set up")
    
    if entry_id:
        if entry_id not in hass.data[DOMAIN]:
            raise ValueError(f"Azure Face entry {entry_id} not found")
        return hass.data[DOMAIN][entry_id]["client"]
    
    # Get the first available entry
    entries = hass.data[DOMAIN]
    if not entries:
        raise ValueError("No Azure Face entries configured")
    
    first_entry = next(iter(entries.values()))
    return first_entry["client"]


async def get_person_group_id(hass: HomeAssistant, entry_id: str = None) -> str:
    """Get person group ID from the first available entry or specified entry."""
    if not hass.data.get(DOMAIN):
        raise ValueError("Azure Face integration not set up")
    
    if entry_id:
        if entry_id not in hass.data[DOMAIN]:
            raise ValueError(f"Azure Face entry {entry_id} not found")
        return hass.data[DOMAIN][entry_id]["person_group_id"]
    
    # Get the first available entry
    entries = hass.data[DOMAIN]
    if not entries:
        raise ValueError("No Azure Face entries configured")
    
    first_entry = next(iter(entries.values()))
    return first_entry["person_group_id"]