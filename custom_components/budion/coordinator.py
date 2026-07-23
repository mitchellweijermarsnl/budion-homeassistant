"""Data update coordinator for Budion."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BudionApiClient, BudionApiError, BudionAuthError
from .birthdays import (
    BirthdayEntry,
    BirthdayPerson,
    collect_birthday_people,
    upcoming_birthdays,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class BudionCoordinatorData:
    """Data fetched from Budion."""

    family: dict[str, Any]
    meal_plan: list[dict[str, Any]] = field(default_factory=list)
    shopping_lists: list[dict[str, Any]] = field(default_factory=list)
    tasks: list[dict[str, Any]] = field(default_factory=list)
    birthday_people: list[BirthdayPerson] = field(default_factory=list)
    birthdays: list[BirthdayEntry] = field(default_factory=list)
    fetched_at: datetime = field(default_factory=datetime.now)


class BudionDataUpdateCoordinator(DataUpdateCoordinator[BudionCoordinatorData]):
    """Coordinator for Budion data."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: BudionApiClient,
        family_id: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.client = client
        self.family_id = family_id

    async def _async_update_data(self) -> BudionCoordinatorData:
        today = date.today()
        week_end = today + timedelta(days=6)

        try:
            family = await self.client.get_family(self.family_id)
        except BudionAuthError as err:
            raise UpdateFailed("Authentication failed") from err
        except BudionApiError as err:
            raise UpdateFailed(str(err)) from err

        meal_plan: list[dict[str, Any]] = []
        shopping_lists: list[dict[str, Any]] = []
        tasks: list[dict[str, Any]] = []
        birthday_people: list[BirthdayPerson] = []
        birthdays: list[BirthdayEntry] = []

        if family.get("has_meal_planning"):
            try:
                plan = await self.client.get_meal_plan(
                    self.family_id,
                    from_date=today.isoformat(),
                    to_date=week_end.isoformat(),
                )
                raw_entries = plan.get("entries", [])
                if isinstance(raw_entries, dict):
                    meal_plan = raw_entries.get("data", [])
                else:
                    meal_plan = raw_entries
            except BudionApiError as err:
                _LOGGER.debug("Meal plan unavailable: %s", err)

            try:
                shopping_lists = await self.client.get_shopping_lists(self.family_id)
            except BudionApiError as err:
                _LOGGER.debug("Shopping lists unavailable: %s", err)

        if family.get("has_shared_tasks"):
            try:
                task_data = await self.client.get_tasks_today(
                    self.family_id,
                    include_overdue=True,
                )
                tasks = task_data.get("items", [])
            except BudionApiError as err:
                _LOGGER.debug("Tasks unavailable: %s", err)

        contacts: list[dict[str, Any]] = []
        members: list[dict[str, Any]] = []

        try:
            members = await self.client.get_members(self.family_id)
        except BudionApiError as err:
            _LOGGER.debug("Members unavailable: %s", err)

        if family.get("has_contacts"):
            try:
                contacts = await self.client.get_contacts(self.family_id)
            except BudionApiError as err:
                _LOGGER.debug("Contacts unavailable: %s", err)

        birthday_people = collect_birthday_people(contacts, members)
        birthdays = upcoming_birthdays(birthday_people, today=today)

        return BudionCoordinatorData(
            family=family,
            meal_plan=meal_plan,
            shopping_lists=shopping_lists,
            tasks=tasks,
            birthday_people=birthday_people,
            birthdays=birthdays,
            fetched_at=datetime.now(),
        )

    def meals_for_date(self, target: date, meal_type: str) -> dict[str, Any] | None:
        """Return a meal plan entry for a specific date and meal type."""
        for entry in self.data.meal_plan:
            if entry.get("date") == target.isoformat() and entry.get("meal_type") == meal_type:
                return entry
        return None

    def meals_for_today(self, meal_type: str) -> dict[str, Any] | None:
        """Return today's meal for a given meal type."""
        return self.meals_for_date(date.today(), meal_type)

    def meal_title(self, entry: dict[str, Any] | None) -> str:
        """Return a display title for a meal entry."""
        if not entry:
            return "Geen planning"
        if entry.get("title"):
            return entry["title"]
        recipe = entry.get("recipe") or {}
        if recipe.get("title"):
            return recipe["title"]
        return "Gepland"
