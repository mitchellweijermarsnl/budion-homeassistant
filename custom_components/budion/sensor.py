"""Sensor platform for Budion."""

from __future__ import annotations

from datetime import date
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .birthdays import format_upcoming_summary, group_upcoming_by_date
from .const import (
    CONF_FAMILY_NAME,
    DOMAIN,
    SENSOR_BIRTHDAYS,
    SENSOR_FAMILY,
    SENSOR_MEAL_BREAKFAST,
    SENSOR_MEAL_DINNER,
    SENSOR_MEAL_LUNCH,
    SENSOR_MEAL_SNACK,
    SENSOR_TASKS,
)
from .coordinator import BudionCoordinatorData, BudionDataUpdateCoordinator

MEAL_SENSOR_DESCRIPTIONS: dict[str, SensorEntityDescription] = {
    SENSOR_MEAL_BREAKFAST: SensorEntityDescription(
        key=SENSOR_MEAL_BREAKFAST,
        translation_key="meal_breakfast",
        icon="mdi:food-croissant",
    ),
    SENSOR_MEAL_LUNCH: SensorEntityDescription(
        key=SENSOR_MEAL_LUNCH,
        translation_key="meal_lunch",
        icon="mdi:food",
    ),
    SENSOR_MEAL_DINNER: SensorEntityDescription(
        key=SENSOR_MEAL_DINNER,
        translation_key="meal_dinner",
        icon="mdi:silverware-fork-knife",
    ),
    SENSOR_MEAL_SNACK: SensorEntityDescription(
        key=SENSOR_MEAL_SNACK,
        translation_key="meal_snack",
        icon="mdi:cookie",
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Budion sensors."""
    domain_data = hass.data[DOMAIN][entry.entry_id]
    coordinator: BudionDataUpdateCoordinator = domain_data["coordinator"]
    family_name: str = entry.data.get(CONF_FAMILY_NAME, entry.title)

    entities: list[SensorEntity] = [
        BudionMealSensor(coordinator, entry, family_name, meal_type, description)
        for meal_type, description in MEAL_SENSOR_DESCRIPTIONS.items()
    ]
    entities.extend(
        [
            BudionTasksSensor(coordinator, entry, family_name),
            BudionBirthdaysSensor(coordinator, entry, family_name),
            BudionFamilySensor(coordinator, entry, family_name),
        ]
    )

    family = coordinator.data.family
    if family.get("has_meal_planning"):
        for shopping_list in coordinator.data.shopping_lists:
            entities.append(
                BudionShoppingListSensor(
                    coordinator,
                    entry,
                    family_name,
                    shopping_list,
                )
            )

    async_add_entities(entities)


class BudionEntity(CoordinatorEntity[BudionDataUpdateCoordinator], SensorEntity):
    """Base Budion entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BudionDataUpdateCoordinator,
        entry: ConfigEntry,
        family_name: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._family_name = family_name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(entry.entry_id))},
            name=family_name,
            manufacturer="Budion",
            model="Family Dashboard",
        )


class BudionMealSensor(BudionEntity):
    """Sensor for a planned meal."""

    def __init__(
        self,
        coordinator: BudionDataUpdateCoordinator,
        entry: ConfigEntry,
        family_name: str,
        meal_type: str,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, entry, family_name)
        self._meal_type = meal_type
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{meal_type}"

    @property
    def native_value(self) -> str:
        """Return today's meal title."""
        entry = self.coordinator.meals_for_today(self._meal_type)
        return self.coordinator.meal_title(entry)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return meal details."""
        entry = self.coordinator.meals_for_today(self._meal_type)
        if not entry:
            return {"date": date.today().isoformat(), "meal_type": self._meal_type}

        recipe = entry.get("recipe") or {}
        return {
            "date": entry.get("date"),
            "meal_type": entry.get("meal_type"),
            "meal_type_label": entry.get("meal_type_label"),
            "title": entry.get("title"),
            "recipe_id": entry.get("recipe_id"),
            "recipe_title": recipe.get("title"),
            "servings": entry.get("servings"),
            "notes": entry.get("notes"),
        }


class BudionTasksSensor(BudionEntity):
    """Sensor for today's tasks."""

    _attr_icon = "mdi:checkbox-marked-circle-outline"
    entity_description = SensorEntityDescription(
        key=SENSOR_TASKS,
        translation_key="tasks_today",
    )

    def __init__(
        self,
        coordinator: BudionDataUpdateCoordinator,
        entry: ConfigEntry,
        family_name: str,
    ) -> None:
        super().__init__(coordinator, entry, family_name)
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_TASKS}"

    @property
    def native_value(self) -> int:
        """Return the number of open tasks."""
        return sum(
            1 for item in self.coordinator.data.tasks if not item.get("is_completed")
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return task details."""
        tasks = []
        for item in self.coordinator.data.tasks:
            task = item.get("task") or {}
            member = item.get("member") or {}
            tasks.append(
                {
                    "title": task.get("title"),
                    "member": member.get("full_name") or member.get("first_name"),
                    "scheduled_for": item.get("scheduled_for"),
                    "is_completed": item.get("is_completed"),
                    "coin_reward": task.get("coin_reward"),
                }
            )

        return {
            "date": date.today().isoformat(),
            "total": len(tasks),
            "completed": sum(1 for item in tasks if item.get("is_completed")),
            "tasks": tasks,
        }


class BudionBirthdaysSensor(BudionEntity):
    """Sensor for upcoming birthdays."""

    _attr_icon = "mdi:cake-variant"
    entity_description = SensorEntityDescription(
        key=SENSOR_BIRTHDAYS,
        translation_key="upcoming_birthdays",
    )

    def __init__(
        self,
        coordinator: BudionDataUpdateCoordinator,
        entry: ConfigEntry,
        family_name: str,
    ) -> None:
        super().__init__(coordinator, entry, family_name)
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_BIRTHDAYS}"

    @property
    def native_value(self) -> str | None:
        """Return the next upcoming birthday date with all names."""
        return format_upcoming_summary(self.coordinator.data.birthdays)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return birthday details."""
        grouped = [
            {
                "date": next_date.isoformat(),
                "days_until": (next_date - date.today()).days,
                "names": [entry.name for entry in day_entries],
                "birthdays": [
                    {
                        "name": entry.name,
                        "birth_date": entry.birth_date.isoformat(),
                        "age": entry.age,
                        "source": entry.source,
                    }
                    for entry in day_entries
                ],
            }
            for next_date, day_entries in group_upcoming_by_date(
                self.coordinator.data.birthdays
            )
        ]

        return {
            "upcoming": grouped,
            "birthdays": [
                {
                    "name": item.name,
                    "birth_date": item.birth_date.isoformat(),
                    "next_occurrence": item.next_occurrence.isoformat(),
                    "days_until": item.days_until,
                    "age": item.age,
                    "source": item.source,
                }
                for item in self.coordinator.data.birthdays
            ],
        }


class BudionFamilySensor(BudionEntity):
    """Sensor exposing family subscription features."""

    _attr_icon = "mdi:home-heart"
    entity_description = SensorEntityDescription(
        key=SENSOR_FAMILY,
        translation_key="family",
    )

    def __init__(
        self,
        coordinator: BudionDataUpdateCoordinator,
        entry: ConfigEntry,
        family_name: str,
    ) -> None:
        super().__init__(coordinator, entry, family_name)
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_FAMILY}"

    @property
    def native_value(self) -> str:
        """Return the family name."""
        return self.coordinator.data.family.get("name", self._family_name)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return family feature flags."""
        family = self.coordinator.data.family
        subscription = family.get("subscription_plan") or {}
        return {
            "family_id": family.get("id"),
            "subscription_plan": subscription.get("name"),
            "has_meal_planning": family.get("has_meal_planning"),
            "has_shared_tasks": family.get("has_shared_tasks"),
            "has_contacts": family.get("has_contacts"),
            "has_budcoins": family.get("has_budcoins"),
            "last_updated": self.coordinator.data.fetched_at.isoformat(),
        }


class BudionShoppingListSensor(BudionEntity):
    """Sensor for a shopping list."""

    _attr_icon = "mdi:cart-outline"

    def __init__(
        self,
        coordinator: BudionDataUpdateCoordinator,
        entry: ConfigEntry,
        family_name: str,
        shopping_list: dict[str, Any],
    ) -> None:
        super().__init__(coordinator, entry, family_name)
        self._list_id = shopping_list["id"]
        self._list_name = shopping_list.get("name", f"Lijst {self._list_id}")
        self._attr_unique_id = f"{entry.entry_id}_shopping_list_{self._list_id}"
        self._attr_translation_key = "shopping_list"
        self._attr_translation_placeholders = {"list_name": self._list_name}

    @property
    def native_value(self) -> int:
        """Return the number of open shopping list items."""
        shopping_list = self._find_list()
        if not shopping_list:
            return 0
        return len(shopping_list.get("open_items") or [])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return shopping list details."""
        shopping_list = self._find_list() or {}
        store = shopping_list.get("store") or {}
        open_items = shopping_list.get("open_items") or []
        checked_items = shopping_list.get("checked_items") or []

        return {
            "list_id": self._list_id,
            "list_name": self._list_name,
            "store": store.get("name"),
            "open_items": [
                {
                    "name": item.get("name"),
                    "quantity": item.get("quantity"),
                    "unit": item.get("unit"),
                }
                for item in open_items
            ],
            "checked_count": len(checked_items),
        }

    def _find_list(self) -> dict[str, Any] | None:
        for shopping_list in self.coordinator.data.shopping_lists:
            if shopping_list.get("id") == self._list_id:
                return shopping_list
        return None
