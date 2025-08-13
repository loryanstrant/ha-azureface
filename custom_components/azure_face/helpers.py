"""Helper functions for the Azure Face integration."""
from homeassistant.core import HomeAssistant

from .azure_client import AzureFaceClient
from .const import DOMAIN


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