import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.discovery import async_load_platform
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Elektrum Energy Monitor component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Elektrum Energy Monitor from a config entry."""
    # Store the config entry data for later use
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Forward the config entry to the sensor platform and await the result
    await hass.config_entries.async_forward_entry_setup(entry, "sensor")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload Elektrum Energy Monitor config entry."""
    # Unload the sensor platform
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")

    # Remove data from hass
    hass.data[DOMAIN].pop(entry.entry_id)

    return True
