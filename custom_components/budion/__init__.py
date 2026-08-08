"""The Budion integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TOKEN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import BudionApiClient
from .const import (
    CONF_BIRTHDAY_DAYS,
    CONF_FAMILY_ID,
    CONF_FAMILY_NAME,
    CONF_SCAN_INTERVAL,
    DEFAULT_API_URL,
    DEFAULT_BIRTHDAY_DAYS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import BudionDataUpdateCoordinator
from .frontend import BudionFrontendRegistration

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.CALENDAR, Platform.TODO]


async def async_setup(hass: HomeAssistant, _config: dict) -> bool:
    """Set up the Budion component and register Lovelace cards early."""
    hass.data.setdefault(DOMAIN, {})
    if not hass.data[DOMAIN].get("frontend_registered"):
        await BudionFrontendRegistration(hass).async_register()
        hass.data[DOMAIN]["frontend_registered"] = True
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Budion from a config entry."""
    # Ensure cards are registered even if async_setup was skipped/raced.
    hass.data.setdefault(DOMAIN, {})
    if not hass.data[DOMAIN].get("frontend_registered"):
        await BudionFrontendRegistration(hass).async_register()
        hass.data[DOMAIN]["frontend_registered"] = True

    session = async_get_clientsession(hass)
    client = BudionApiClient(session, DEFAULT_API_URL, entry.data[CONF_TOKEN])

    birthday_days = entry.options.get(CONF_BIRTHDAY_DAYS, DEFAULT_BIRTHDAY_DAYS)
    coordinator = BudionDataUpdateCoordinator(
        hass,
        client,
        entry.data[CONF_FAMILY_ID],
        birthday_days=int(birthday_days),
    )

    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL,
        int(DEFAULT_SCAN_INTERVAL.total_seconds()),
    )
    coordinator.update_interval = timedelta(seconds=scan_interval)

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "client": client,
        "family_name": entry.data.get(CONF_FAMILY_NAME, entry.title),
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
