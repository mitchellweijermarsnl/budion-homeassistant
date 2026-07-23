"""The Budion integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TOKEN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import BudionApiClient
from .const import CONF_FAMILY_ID, CONF_FAMILY_NAME, DEFAULT_API_URL, DEFAULT_SCAN_INTERVAL, DOMAIN
from .coordinator import BudionDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.CALENDAR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Budion from a config entry."""
    session = async_get_clientsession(hass)
    client = BudionApiClient(session, DEFAULT_API_URL, entry.data[CONF_TOKEN])

    coordinator = BudionDataUpdateCoordinator(
        hass,
        client,
        entry.data[CONF_FAMILY_ID],
    )

    scan_interval = entry.options.get(
        "scan_interval",
        int(DEFAULT_SCAN_INTERVAL.total_seconds()),
    )
    coordinator.update_interval = timedelta(seconds=scan_interval)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "client": client,
        "family_name": entry.data.get(CONF_FAMILY_NAME, entry.title),
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
