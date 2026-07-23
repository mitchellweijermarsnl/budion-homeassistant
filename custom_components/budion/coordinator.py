"""Data update coordinator for Budion."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BudionApiClient, BudionApiError, BudionAuthError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class BirthdayEntry:
    """An upcoming birthday."""

    name: str
    birth_date: str
    days_until: int
    age: int | None
    source: str


@dataclass
class BudionCoordinatorData:
    """Data fetched from Budion."""

    family: dict[str, Any]
    meal_plan: list[dict[str, Any]] = field(default_factory=list)
    shopping_lists: list[dict[str, Any]] = field(default_factory=list)
    tasks: list[dict[str, Any]] = field(default_factory=list)
    birthdays: list[BirthdayEntry] = field(default_factory=list)
    fetched_at: datetime = field(default_factory=datetime.now)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _next_birthday(birth: date, *, year_known: bool, today: date) -> tuple[date, int | None]:
    """Return the next birthday date and age if year is known."""
    try:
        candidate = birth.replace(year=today.year)
    except ValueError:
        candidate = date(today.year, 2, 28)

    if candidate < today:
        try:
            candidate = birth.replace(year=today.year + 1)
        except ValueError:
            candidate = date(today.year + 1, 2, 28)

    age = None
    if year_known:
        age = candidate.year - birth.year

    return candidate, age


def _collect_birthdays(
    contacts: list[dict[str, Any]],
    members: list[dict[str, Any]],
    *,
    today: date,
    horizon_days: int = 60,
) -> list[BirthdayEntry]:
    """Collect upcoming birthdays from contacts and family members."""
    entries: list[BirthdayEntry] = []

    for contact in contacts:
        birth = _parse_date(contact.get("birth_date"))
        if birth is None:
            continue
        next_date, age = _next_birthday(
            birth,
            year_known=contact.get("birth_year_known", True),
            today=today,
        )
        days = (next_date - today).days
        if days <= horizon_days:
            entries.append(
                BirthdayEntry(
                    name=contact.get("full_name") or contact.get("first_name", "Onbekend"),
                    birth_date=birth.isoformat(),
                    days_until=days,
                    age=age,
                    source="contact",
                )
            )

    for member in members:
        person = member.get("person") or {}
        birth = _parse_date(person.get("birth_date"))
        if birth is None:
            continue
        next_date, age = _next_birthday(birth, year_known=True, today=today)
        days = (next_date - today).days
        if days <= horizon_days:
            entries.append(
                BirthdayEntry(
                    name=person.get("full_name") or person.get("first_name", "Onbekend"),
                    birth_date=birth.isoformat(),
                    days_until=days,
                    age=age,
                    source="member",
                )
            )

    entries.sort(key=lambda item: item.days_until)
    return entries


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

        if family.get("has_contacts"):
            contacts: list[dict[str, Any]] = []
            members: list[dict[str, Any]] = []
            try:
                contacts = await self.client.get_contacts(self.family_id)
            except BudionApiError as err:
                _LOGGER.debug("Contacts unavailable: %s", err)
            try:
                members = await self.client.get_members(self.family_id)
            except BudionApiError as err:
                _LOGGER.debug("Members unavailable: %s", err)

            birthdays = _collect_birthdays(contacts, members, today=today)

        return BudionCoordinatorData(
            family=family,
            meal_plan=meal_plan,
            shopping_lists=shopping_lists,
            tasks=tasks,
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
