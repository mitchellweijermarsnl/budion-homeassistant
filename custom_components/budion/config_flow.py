"""Config flow for Budion."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from aiohttp import ClientConnectorError
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_TOKEN
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    BudionApiClient,
    BudionApiError,
    BudionAuthError,
    BudionTwoFactorRequired,
)
from .const import (
    CONF_BIRTHDAY_DAYS,
    CONF_EMAIL,
    CONF_FAMILY_ID,
    CONF_FAMILY_NAME,
    CONF_SCAN_INTERVAL,
    DEFAULT_API_URL,
    DEFAULT_BIRTHDAY_DAYS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

STEP_TWO_FACTOR_SCHEMA = vol.Schema(
    {
        vol.Required("code"): str,
        vol.Optional("recovery", default=False): bool,
    }
)


async def _validate_login(
    hass: HomeAssistant,
    email: str,
    password: str,
) -> tuple[str, list[dict[str, Any]]]:
    session = async_get_clientsession(hass)
    client = BudionApiClient(session, DEFAULT_API_URL)
    token = await client.login(email, password)
    families = await client.get_families()
    return token, families


class BudionConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Budion."""

    VERSION = 2

    def __init__(self) -> None:
        self._email: str | None = None
        self._password: str | None = None
        self._challenge_token: str | None = None
        self._families: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._email = user_input[CONF_EMAIL]
            self._password = user_input[CONF_PASSWORD]

            try:
                token, families = await _validate_login(
                    self.hass,
                    self._email,
                    self._password,
                )
            except BudionTwoFactorRequired as err:
                self._challenge_token = err.challenge_token
                return await self.async_step_two_factor()
            except BudionAuthError:
                errors["base"] = "invalid_auth"
            except BudionApiError:
                errors["base"] = "cannot_connect"
            except ClientConnectorError:
                errors["base"] = "cannot_connect"
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            else:
                return await self._async_create_or_select_family(token, families)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_two_factor(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle two-factor authentication."""
        errors: dict[str, str] = {}

        if user_input is not None and self._challenge_token:
            session = async_get_clientsession(self.hass)
            client = BudionApiClient(session, DEFAULT_API_URL)

            try:
                token = await client.complete_two_factor(
                    self._challenge_token,
                    user_input["code"],
                    recovery=user_input.get("recovery", False),
                )
                families = await client.get_families()
            except BudionAuthError:
                errors["base"] = "invalid_auth"
            except BudionApiError:
                errors["base"] = "cannot_connect"
            except ClientConnectorError:
                errors["base"] = "cannot_connect"
            else:
                return await self._async_create_or_select_family(token, families)

        return self.async_show_form(
            step_id="two_factor",
            data_schema=STEP_TWO_FACTOR_SCHEMA,
            errors=errors,
        )

    async def _async_create_or_select_family(
        self,
        token: str,
        families: list[dict[str, Any]],
    ) -> FlowResult:
        if not families:
            return self.async_abort(reason="no_families")

        if len(families) == 1:
            family = families[0]
            return self.async_create_entry(
                title=family.get("name", "Budion"),
                data={
                    CONF_TOKEN: token,
                    CONF_EMAIL: self._email,
                    CONF_FAMILY_ID: family["id"],
                    CONF_FAMILY_NAME: family.get("name", "Budion"),
                },
            )

        self._families = families
        self.context["login_token"] = token
        return await self.async_step_family()

    async def async_step_family(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let the user pick a family when multiple are available."""
        errors: dict[str, str] = {}
        token = self.context.get("login_token")

        if user_input is not None and token:
            family_id = int(user_input[CONF_FAMILY_ID])
            family = next(
                (item for item in self._families if item["id"] == family_id),
                None,
            )
            if family is None:
                errors["base"] = "family_not_found"
            else:
                return self.async_create_entry(
                    title=family.get("name", "Budion"),
                    data={
                        CONF_TOKEN: token,
                        CONF_EMAIL: self._email,
                        CONF_FAMILY_ID: family_id,
                        CONF_FAMILY_NAME: family.get("name", "Budion"),
                    },
                )

        family_map = {
            str(item["id"]): item.get("name", f"Familie {item['id']}")
            for item in self._families
        }

        return self.async_show_form(
            step_id="family",
            data_schema=vol.Schema({vol.Required(CONF_FAMILY_ID): vol.In(family_map)}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow handler."""
        return BudionOptionsFlowHandler(config_entry)


class BudionOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Budion options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        scan_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            int(DEFAULT_SCAN_INTERVAL.total_seconds()),
        )
        birthday_days = self.config_entry.options.get(
            CONF_BIRTHDAY_DAYS,
            DEFAULT_BIRTHDAY_DAYS,
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=scan_interval,
                    ): vol.All(vol.Coerce(int), vol.Range(min=60, max=3600)),
                    vol.Required(
                        CONF_BIRTHDAY_DAYS,
                        default=birthday_days,
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=365)),
                }
            ),
        )
