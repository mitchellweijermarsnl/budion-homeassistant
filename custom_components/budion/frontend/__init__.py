"""Frontend resources for Budion Lovelace cards."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later

from ..const import FRONTEND_URL_BASE, INTEGRATION_VERSION, JSMODULES

_LOGGER = logging.getLogger(__name__)


class BudionFrontendRegistration:
    """Register Budion JavaScript modules with Home Assistant."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.lovelace = self.hass.data.get("lovelace")

    async def async_register(self) -> None:
        """Register static paths and Lovelace resources."""
        await self._async_register_path()
        if self.lovelace is None:
            _LOGGER.debug("Lovelace not available; skipping resource registration")
            return
        mode = getattr(self.lovelace, "mode", None)
        if mode != "storage":
            _LOGGER.debug(
                "Lovelace mode is %s; add %s manually if needed",
                mode,
                FRONTEND_URL_BASE,
            )
            return
        await self._async_wait_for_lovelace_resources()

    async def _async_register_path(self) -> None:
        """Serve the frontend directory."""
        try:
            await self.hass.http.async_register_static_paths(
                [
                    StaticPathConfig(
                        FRONTEND_URL_BASE,
                        str(Path(__file__).parent),
                        False,
                    )
                ]
            )
        except RuntimeError:
            _LOGGER.debug("Budion frontend path already registered")

    async def _async_wait_for_lovelace_resources(self) -> None:
        """Wait until Lovelace resources are ready."""

        async def _check_loaded(_now: Any) -> None:
            resources = getattr(self.lovelace, "resources", None)
            if resources is not None and getattr(resources, "loaded", False):
                await self._async_register_modules()
                return
            async_call_later(self.hass, 5, _check_loaded)

        await _check_loaded(0)

    async def _async_register_modules(self) -> None:
        """Install or update Lovelace module resources."""
        resources = self.lovelace.resources
        existing = [
            item
            for item in resources.async_items()
            if str(item.get("url", "")).startswith(FRONTEND_URL_BASE)
        ]

        for module in JSMODULES:
            url = f"{FRONTEND_URL_BASE}/{module['filename']}"
            versioned = f"{url}?v={module['version']}"
            matched = None
            for item in existing:
                if self._path(item.get("url", "")) == url:
                    matched = item
                    break

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

    @staticmethod
    def _path(url: str) -> str:
        return url.split("?", 1)[0]

    @staticmethod
    def _version(url: str) -> str | None:
        if "?v=" not in url:
            return None
        return url.rsplit("?v=", 1)[-1]
