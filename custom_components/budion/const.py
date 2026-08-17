"""Constants for the Budion integration."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from typing import Final

DOMAIN: Final = "budion"

_MANIFEST_PATH = Path(__file__).parent / "manifest.json"
with _MANIFEST_PATH.open(encoding="utf-8") as _manifest_file:
    INTEGRATION_VERSION: Final[str] = json.load(_manifest_file).get("version", "0.0.0")

FRONTEND_URL_BASE: Final = f"/{DOMAIN}-frontend"
JSMODULES: Final = [
    {
        "name": "Budion Verjaardagen",
        "filename": "budion-birthdays-card.js",
        "version": INTEGRATION_VERSION,
    },
]

# Production API (backend for app.budion.com).
DEFAULT_API_URL: Final = "https://api.budion.com"

CONF_URL: Final = "url"
CONF_TOKEN: Final = "token"
CONF_FAMILY_ID: Final = "family_id"
CONF_FAMILY_NAME: Final = "family_name"
CONF_EMAIL: Final = "email"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_BIRTHDAY_DAYS: Final = "birthday_days"

DEFAULT_SCAN_INTERVAL: Final = timedelta(minutes=5)
# 365 ≈ everyone's next birthday once; lower values filter the dashboard sensors.
DEFAULT_BIRTHDAY_DAYS: Final = 365
API_PREFIX: Final = "/api/v1"
DEVICE_NAME: Final = "Home Assistant"

MEAL_TYPES: Final = ("breakfast", "lunch", "dinner", "snack")
# Matches Family::resolvedMealPlanEnabledTypes() when unset.
DEFAULT_ENABLED_MEAL_TYPES: Final = ("lunch", "dinner")

SENSOR_MEAL_BREAKFAST: Final = "meal_breakfast"
SENSOR_MEAL_LUNCH: Final = "meal_lunch"
SENSOR_MEAL_DINNER: Final = "meal_dinner"
SENSOR_MEAL_SNACK: Final = "meal_snack"
SENSOR_TASKS: Final = "tasks_today"
SENSOR_BIRTHDAYS: Final = "upcoming_birthdays"
SENSOR_FAMILY: Final = "family"

MEAL_SENSOR_API_TYPES: Final = {
    SENSOR_MEAL_BREAKFAST: "breakfast",
    SENSOR_MEAL_LUNCH: "lunch",
    SENSOR_MEAL_DINNER: "dinner",
    SENSOR_MEAL_SNACK: "snack",
}

MEAL_API_TYPE_SENSORS: Final = {
    api_type: sensor_key for sensor_key, api_type in MEAL_SENSOR_API_TYPES.items()
}

SENSOR_TYPES: Final = (
    SENSOR_MEAL_BREAKFAST,
    SENSOR_MEAL_LUNCH,
    SENSOR_MEAL_DINNER,
    SENSOR_MEAL_SNACK,
    SENSOR_TASKS,
    SENSOR_BIRTHDAYS,
    SENSOR_FAMILY,
)
