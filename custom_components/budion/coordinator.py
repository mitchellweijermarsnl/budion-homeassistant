"""Data update coordinator for Budion."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BudionApiClient, BudionApiError, BudionAuthError
from .birthdays import (
    BirthdayEntry,
    BirthdayPerson,
    collect_birthday_people,
    upcoming_birthdays,
)
from .const import (
    DEFAULT_BIRTHDAY_DAYS,
    DEFAULT_ENABLED_MEAL_TYPES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MEAL_TYPES,
)
from .food_icons import food_icon_to_mdi
from .members import ChildMember, build_children

_LOGGER = logging.getLogger(__name__)


@dataclass
class BudionCoordinatorData:
    """Data fetched from Budion."""

    family: dict[str, Any]
    meal_plan: list[dict[str, Any]] = field(default_factory=list)
    tasks: list[dict[str, Any]] = field(default_factory=list)
    birthday_people: list[BirthdayPerson] = field(default_factory=list)
    birthdays: list[BirthdayEntry] = field(default_factory=list)
    children: list[ChildMember] = field(default_factory=list)
    fetched_at: datetime = field(default_factory=datetime.now)


class BudionDataUpdateCoordinator(DataUpdateCoordinator[BudionCoordinatorData]):
    """Coordinator for Budion data."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: BudionApiClient,
        family_id: int,
        *,
        birthday_days: int = DEFAULT_BIRTHDAY_DAYS,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.client = client
        self.family_id = family_id
        self.birthday_days = birthday_days

    async def _async_update_data(self) -> BudionCoordinatorData:
        today = dt_util.now().date()
        week_end = today + timedelta(days=6)

        try:
            family = await self.client.get_family(self.family_id)
        except BudionAuthError as err:
            raise UpdateFailed("Authentication failed") from err
        except BudionApiError as err:
            raise UpdateFailed(str(err)) from err

        meal_plan: list[dict[str, Any]] = []
        tasks: list[dict[str, Any]] = []
        wallets: list[dict[str, Any]] = []
        birthday_people: list[BirthdayPerson] = []
        birthdays: list[BirthdayEntry] = []
        children: list[ChildMember] = []

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
                _LOGGER.warning("Meal plan unavailable: %s", err)

        if family.get("has_shared_tasks"):
            try:
                task_data = await self.client.get_tasks_today(
                    self.family_id,
                    include_overdue=True,
                )
                tasks = task_data.get("items", [])
            except BudionApiError as err:
                _LOGGER.debug("Tasks unavailable: %s", err)

        if family.get("has_budcoins"):
            try:
                wallets = await self.client.get_wallets(self.family_id)
            except BudionApiError as err:
                _LOGGER.debug("Wallets unavailable: %s", err)

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
        birthdays = upcoming_birthdays(
            birthday_people,
            today=today,
            horizon_days=self.birthday_days,
        )
        children = build_children(members, wallets, tasks)

        return BudionCoordinatorData(
            family=family,
            meal_plan=meal_plan,
            tasks=tasks,
            birthday_people=birthday_people,
            birthdays=birthdays,
            children=children,
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
        return self.meals_for_date(dt_util.now().date(), meal_type)

    @staticmethod
    def recipe_from_entry(entry: dict[str, Any]) -> dict[str, Any]:
        """Return the recipe payload from a meal plan entry."""
        recipe = entry.get("recipe") or {}
        if isinstance(recipe, dict) and isinstance(recipe.get("data"), dict):
            return recipe["data"]
        return recipe if isinstance(recipe, dict) else {}

    def meal_title(self, entry: dict[str, Any] | None) -> str:
        """Return a display title for a meal entry."""
        if not entry:
            return "Geen planning"
        if entry.get("title"):
            return entry["title"]
        recipe = self.recipe_from_entry(entry)
        if recipe.get("title"):
            return recipe["title"]
        return "Gepland"

    def meal_image_url(self, entry: dict[str, Any] | None) -> str | None:
        """Return the recipe image URL for a meal entry."""
        if not entry:
            return None
        image_url = self.recipe_from_entry(entry).get("image_url")
        return image_url if image_url else None

    def meal_icon_id(self, entry: dict[str, Any] | None) -> str | None:
        """Return the Budion food-icon id for a meal entry."""
        if not entry:
            return None
        icon = entry.get("icon")
        return icon if isinstance(icon, str) and icon.strip() else None

    def meal_mdi_icon(self, entry: dict[str, Any] | None, fallback: str) -> str:
        """Return an mdi icon for a meal entry, falling back when unknown."""
        return food_icon_to_mdi(self.meal_icon_id(entry)) or fallback

    def enabled_meal_types(self) -> tuple[str, ...]:
        """Return meal types enabled for the family meal plan."""
        settings = self.data.family.get("meal_plan_settings") or {}
        configured = settings.get("enabled_meal_types")
        if isinstance(configured, list):
            enabled = tuple(
                meal_type
                for meal_type in configured
                if isinstance(meal_type, str) and meal_type in MEAL_TYPES
            )
            if enabled:
                return enabled
        return DEFAULT_ENABLED_MEAL_TYPES

    def child_by_membership_id(self, membership_id: int) -> ChildMember | None:
        """Return a child member by membership ID."""
        for child in self.data.children:
            if child.membership_id == membership_id:
                return child
        return None

    def birthday_by_key(self, key: str) -> BirthdayEntry | None:
        """Return an upcoming birthday entry by person key."""
        for entry in self.data.birthdays:
            if entry.key == key:
                return entry
        return None
