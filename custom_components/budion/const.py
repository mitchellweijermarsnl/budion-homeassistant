"""Constants for the Budion integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "budion"

CONF_URL: Final = "url"
CONF_TOKEN: Final = "token"
CONF_FAMILY_ID: Final = "family_id"
CONF_FAMILY_NAME: Final = "family_name"
CONF_EMAIL: Final = "email"

DEFAULT_SCAN_INTERVAL: Final = timedelta(minutes=5)
API_PREFIX: Final = "/api/v1"
DEVICE_NAME: Final = "Home Assistant"

MEAL_TYPES: Final = ("breakfast", "lunch", "dinner", "snack")

SENSOR_MEAL_BREAKFAST: Final = "meal_breakfast"
SENSOR_MEAL_LUNCH: Final = "meal_lunch"
SENSOR_MEAL_DINNER: Final = "meal_dinner"
SENSOR_MEAL_SNACK: Final = "meal_snack"
SENSOR_TASKS: Final = "tasks_today"
SENSOR_BIRTHDAYS: Final = "upcoming_birthdays"
SENSOR_FAMILY: Final = "family"

SENSOR_TYPES: Final = (
    SENSOR_MEAL_BREAKFAST,
    SENSOR_MEAL_LUNCH,
    SENSOR_MEAL_DINNER,
    SENSOR_MEAL_SNACK,
    SENSOR_TASKS,
    SENSOR_BIRTHDAYS,
    SENSOR_FAMILY,
)
