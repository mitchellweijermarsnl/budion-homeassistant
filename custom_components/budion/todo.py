"""Todo platform for Budion shopping lists."""

from __future__ import annotations

from typing import Any

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import BudionApiError
from .const import CONF_FAMILY_NAME, DOMAIN
from .coordinator import BudionDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Budion shopping list todo entities."""
    domain_data = hass.data[DOMAIN][entry.entry_id]
    coordinator: BudionDataUpdateCoordinator = domain_data["coordinator"]
    family_name: str = entry.data.get(CONF_FAMILY_NAME, entry.title)

    if not coordinator.data.family.get("has_meal_planning"):
        return

    entities = [
        BudionShoppingTodoList(
            coordinator,
            entry,
            family_name,
            shopping_list,
        )
        for shopping_list in coordinator.data.shopping_lists
        if shopping_list.get("id") is not None
    ]
    async_add_entities(entities)


def _quantity_description(item: dict[str, Any]) -> str | None:
    """Return a compact quantity/unit description for a shopping item."""
    quantity = item.get("quantity")
    unit = item.get("unit")
    parts: list[str] = []
    if quantity not in (None, ""):
        parts.append(str(quantity))
    if unit not in (None, ""):
        parts.append(str(unit))
    if not parts:
        return None
    return " ".join(parts)


class BudionShoppingTodoList(
    CoordinatorEntity[BudionDataUpdateCoordinator], TodoListEntity
):
    """Interactive Budion shopping list."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:cart-outline"
    _attr_translation_key = "shopping_list"
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.MOVE_TODO_ITEM
    )

    def __init__(
        self,
        coordinator: BudionDataUpdateCoordinator,
        entry: ConfigEntry,
        family_name: str,
        shopping_list: dict[str, Any],
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._list_id = int(shopping_list["id"])
        self._list_name = shopping_list.get("name", f"Lijst {self._list_id}")
        self._attr_unique_id = f"{entry.entry_id}_todo_shopping_list_{self._list_id}"
        self._attr_translation_placeholders = {"list_name": self._list_name}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(entry.entry_id))},
            name=family_name,
            manufacturer="Budion",
            model="Family Dashboard",
        )

    @property
    def shopping_list(self) -> dict[str, Any] | None:
        """Return the latest shopping list payload."""
        return self.coordinator.shopping_list_by_id(self._list_id)

    @property
    def todo_items(self) -> list[TodoItem]:
        """Return open and checked shopping items."""
        shopping_list = self.shopping_list
        items: list[TodoItem] = []

        for item in self.coordinator.shopping_list_items(shopping_list, checked=False):
            item_id = item.get("id")
            name = item.get("name")
            if item_id is None or not name:
                continue
            items.append(
                TodoItem(
                    uid=str(item_id),
                    summary=str(name),
                    description=_quantity_description(item),
                    status=TodoItemStatus.NEEDS_ACTION,
                )
            )

        for item in self.coordinator.shopping_list_items(shopping_list, checked=True):
            item_id = item.get("id")
            name = item.get("name")
            if item_id is None or not name:
                continue
            items.append(
                TodoItem(
                    uid=str(item_id),
                    summary=str(name),
                    description=_quantity_description(item),
                    status=TodoItemStatus.COMPLETED,
                )
            )

        return items

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Add an item to the Budion shopping list."""
        if not item.summary:
            raise HomeAssistantError("Shopping list item name is required")

        try:
            await self.coordinator.client.create_shopping_list_item(
                self.coordinator.family_id,
                self._list_id,
                name=item.summary,
            )
        except BudionApiError as err:
            raise HomeAssistantError(f"Could not add shopping list item: {err}") from err

        await self.coordinator.async_request_refresh()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update an item name or checked state."""
        if not item.uid:
            raise HomeAssistantError("Shopping list item id is required")

        fields: dict[str, Any] = {}
        if item.summary:
            fields["name"] = item.summary
        if item.status == TodoItemStatus.COMPLETED:
            fields["is_checked"] = True
        elif item.status == TodoItemStatus.NEEDS_ACTION:
            fields["is_checked"] = False

        if not fields:
            return

        try:
            await self.coordinator.client.update_shopping_list_item(
                self.coordinator.family_id,
                self._list_id,
                int(item.uid),
                **fields,
            )
        except BudionApiError as err:
            raise HomeAssistantError(
                f"Could not update shopping list item: {err}"
            ) from err
        except ValueError as err:
            raise HomeAssistantError("Invalid shopping list item id") from err

        await self.coordinator.async_request_refresh()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete one or more shopping list items."""
        for uid in uids:
            try:
                await self.coordinator.client.delete_shopping_list_item(
                    self.coordinator.family_id,
                    self._list_id,
                    int(uid),
                )
            except BudionApiError as err:
                raise HomeAssistantError(
                    f"Could not delete shopping list item: {err}"
                ) from err
            except ValueError as err:
                raise HomeAssistantError("Invalid shopping list item id") from err

        await self.coordinator.async_request_refresh()

    async def async_move_todo_item(
        self, uid: str, previous_uid: str | None = None
    ) -> None:
        """Reorder an item within its open or checked group."""
        shopping_list = self.shopping_list
        if not shopping_list:
            raise HomeAssistantError("Shopping list not found")

        try:
            item_id = int(uid)
        except ValueError as err:
            raise HomeAssistantError("Invalid shopping list item id") from err

        open_ids = [
            int(item["id"])
            for item in self.coordinator.shopping_list_items(
                shopping_list, checked=False
            )
            if item.get("id") is not None
        ]
        checked_ids = [
            int(item["id"])
            for item in self.coordinator.shopping_list_items(
                shopping_list, checked=True
            )
            if item.get("id") is not None
        ]

        if item_id in open_ids:
            item_ids = open_ids
            checked = False
        elif item_id in checked_ids:
            item_ids = checked_ids
            checked = True
        else:
            raise HomeAssistantError("Shopping list item not found")

        item_ids = [value for value in item_ids if value != item_id]
        if previous_uid is None:
            item_ids.insert(0, item_id)
        else:
            try:
                previous_id = int(previous_uid)
            except ValueError as err:
                raise HomeAssistantError("Invalid previous shopping list item id") from err
            if previous_id not in item_ids:
                raise HomeAssistantError("Previous shopping list item not found")
            insert_at = item_ids.index(previous_id) + 1
            item_ids.insert(insert_at, item_id)

        try:
            await self.coordinator.client.reorder_shopping_list_items(
                self.coordinator.family_id,
                self._list_id,
                item_ids,
                checked=checked,
            )
        except BudionApiError as err:
            raise HomeAssistantError(
                f"Could not reorder shopping list items: {err}"
            ) from err

        await self.coordinator.async_request_refresh()
