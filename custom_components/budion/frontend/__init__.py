"""Frontend resources for Budion Lovelace cards."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later

from ..const import FRONTEND_URL_BASE, JSMODULES

_LOGGER = logging.getLogger(__name__)
_WWW_PATH = Path(__file__).parent / "www"


class BudionFrontendRegistration:
    """Register Budion JavaScript modules with Home Assistant."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def async_register(self) -> None:
        """Register static paths and ensure cards are loaded by the frontend."""
        await self._async_register_path()

        # Always register as frontend modules so cards load on every page,
        # including the card picker. This avoids cold-start races.
        for module in JSMODULES:
            add_extra_js_url(self.hass, self._versioned_url(module))

        lovelace = self.hass.data.get("lovelace")
        if lovelace is None:
            _LOGGER.warning(
                "Lovelace not ready yet; Budion cards are loaded via frontend modules"
            )
            return

        mode = getattr(lovelace, "mode", None)
        if mode == "storage":
            await self._async_wait_for_lovelace_resources(lovelace)
        else:
            _LOGGER.debug(
                "Lovelace mode is %s; cards are available via frontend modules at %s",
                mode,
                FRONTEND_URL_BASE,
            )

    async def _async_register_path(self) -> None:
        """Serve the www directory with the card JavaScript files."""
        try:
            await self.hass.http.async_register_static_paths(
                [StaticPathConfig(FRONTEND_URL_BASE, str(_WWW_PATH), False)]
            )
            _LOGGER.debug(
                "Registered Budion frontend path %s -> %s",
                FRONTEND_URL_BASE,
                _WWW_PATH,
            )
        except RuntimeError:
            _LOGGER.debug("Budion frontend path already registered")

    async def _async_wait_for_lovelace_resources(self, lovelace: Any) -> None:
        """Wait until Lovelace resources are ready, then mirror modules there."""

        async def _check_loaded(_now: Any = None) -> None:
            resources = getattr(lovelace, "resources", None)
            if resources is not None and getattr(resources, "loaded", False):
                await self._async_register_lovelace_modules(resources)
                return
            async_call_later(self.hass, 5, _check_loaded)

        await _check_loaded()

    async def _async_register_lovelace_modules(self, resources: Any) -> None:
        """Install or update Lovelace module resources (storage mode)."""
        try:
            existing_items = list(resources.async_items())
        except Exception:  # noqa: BLE001 - keep frontend load resilient
            _LOGGER.exception("Could not read Lovelace resources")
            return

        existing = [
            item
            for item in existing_items
            if str(item.get("url", "")).startswith(FRONTEND_URL_BASE)
        ]

        for module in JSMODULES:
            url = f"{FRONTEND_URL_BASE}/{module['filename']}"
            versioned = self._versioned_url(module)
            matched = next(
                (
                    item
                    for item in existing
                    if self._path(item.get("url", "")) == url
                ),
                None,
            )

            try:
                if matched is None:
                    _LOGGER.info("Registering Lovelace module %s", module["name"])
                    await resources.async_create_item(
                        {"res_type": "module", "url": versioned}
                    )
                    continue

                if self._version(matched.get("url", "")) != module["version"]:
                    _LOGGER.info(
                        "Updating Lovelace module %s to %s",
                        module["name"],
                        module["version"],
                    )
                    await resources.async_update_item(
                        matched["id"],
                        {"res_type": "module", "url": versioned},
                    )
            except Exception:  # noqa: BLE001 - keep frontend load resilient
                _LOGGER.exception(
                    "Could not register Lovelace module %s", module["name"]
                )

        known_urls = {
            f"{FRONTEND_URL_BASE}/{module['filename']}" for module in JSMODULES
        }
        for item in existing:
            if self._path(item.get("url", "")) in known_urls:
                continue
            try:
                _LOGGER.info("Removing unused Lovelace module %s", item.get("url"))
                await resources.async_delete_item(item["id"])
            except Exception:  # noqa: BLE001 - keep frontend load resilient
                _LOGGER.exception(
                    "Could not remove Lovelace module %s", item.get("url")
                )

    @staticmethod
    def _versioned_url(module: dict[str, str]) -> str:
        return f"{FRONTEND_URL_BASE}/{module['filename']}?v={module['version']}"

    @staticmethod
    def _path(url: str) -> str:
        return url.split("?", 1)[0]

    @staticmethod
    def _version(url: str) -> str | None:
        if "?v=" not in url:
            return None
        return url.rsplit("?v=", 1)[-1]
