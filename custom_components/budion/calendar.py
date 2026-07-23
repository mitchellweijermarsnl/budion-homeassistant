"""Calendar platform for Budion birthdays."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.components.calendar import (
    CalendarEntity,
    CalendarEntityDescription,
    CalendarEvent,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .birthdays import birthday_events_in_range, upcoming_birthdays
from .const import CONF_FAMILY_NAME, DOMAIN
from .coordinator import BudionDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

try:
    CALENDAR_DESCRIPTION = CalendarEntityDescription(
        key="birthdays",
        translation_key="birthdays",
        icon="mdi:cake-variant",
        initial_color="#ff0072",
    )
except TypeError:
    CALENDAR_DESCRIPTION = CalendarEntityDescription(
        key="birthdays",
        translation_key="birthdays",
        icon="mdi:cake-variant",
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Budion calendar entities."""
    coordinator: BudionDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    family_name: str = entry.data.get(CONF_FAMILY_NAME, entry.title)

    _LOGGER.debug(
        "Registering Budion birthday calendar (%s people)",
        len(coordinator.data.birthday_people),
    )

    async_add_entities(
        [BudionBirthdayCalendar(coordinator, entry, family_name)],
        update_before_add=True,
    )


class BudionBirthdayCalendar(CoordinatorEntity[BudionDataUpdateCoordinator], CalendarEntity):
    """Calendar with all Budion birthdays."""

    entity_description = CALENDAR_DESCRIPTION
    _attr_has_entity_name = True
    _attr_initial_color = "#ff0072"

    def __init__(
        self,
        coordinator: BudionDataUpdateCoordinator,
        entry: ConfigEntry,
        family_name: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_birthdays_calendar"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(entry.entry_id))},
            name=family_name,
            manufacturer="Budion",
            model="Family Dashboard",
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming birthday event."""
        entries = upcoming_birthdays(self.coordinator.data.birthday_people)
        if not entries:
            return None

        next_entry = entries[0]
        same_day = [
            item
            for item in entries
            if item.next_occurrence == next_entry.next_occurrence
        ]

        if len(same_day) == 1:
            summary = next_entry.name
            if next_entry.age is not None:
                summary = f"{next_entry.name} ({next_entry.age})"
        else:
            summary = ", ".join(item.name for item in same_day)

        return CalendarEvent(
            uid=f"{next_entry.key}-{next_entry.next_occurrence.year}",
            summary=summary,
            start=next_entry.next_occurrence,
            end=next_entry.next_occurrence + timedelta(days=1),
            description=f"{len(same_day)} verjaardag(en)",
        )

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return birthday events in a date range."""
        return birthday_events_in_range(
            self.coordinator.data.birthday_people,
            start_date,
            end_date,
        )
