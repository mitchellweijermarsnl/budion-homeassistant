"""Budion API client."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urljoin

import aiohttp
from aiohttp import ClientResponseError

from .const import API_PREFIX, DEVICE_NAME

_LOGGER = logging.getLogger(__name__)


class BudionAuthError(Exception):
    """Authentication failed."""


class BudionTwoFactorRequired(Exception):
    """Two-factor authentication is required."""

    def __init__(self, challenge_token: str) -> None:
        super().__init__("Two-factor authentication required")
        self.challenge_token = challenge_token


class BudionApiError(Exception):
    """Generic API error."""


class BudionApiClient:
    """Async client for the Budion API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        token: str | None = None,
        *,
        locale: str = "nl",
    ) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._locale = locale

    @property
    def token(self) -> str | None:
        """Return the current API token."""
        return self._token

    def _url(self, path: str) -> str:
        return urljoin(f"{self._base_url}{API_PREFIX}/", path.lstrip("/"))

    def _headers(self, *, auth: bool = True) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Accept-Language": self._locale,
        }
        if auth and self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        *,
        auth: bool = True,
        expected_status: int | tuple[int, ...] = (200, 201),
        **kwargs: Any,
    ) -> dict[str, Any] | list[Any] | None:
        url = self._url(path)
        try:
            async with self._session.request(
                method,
                url,
                headers=self._headers(auth=auth),
                **kwargs,
            ) as response:
                if isinstance(expected_status, int):
                    expected = (expected_status,)
                else:
                    expected = expected_status

                if response.status not in expected:
                    body = await response.text()
                    _LOGGER.debug(
                        "Budion API error %s %s: %s",
                        response.status,
                        url,
                        body,
                    )
                    if response.status in (401, 403):
                        raise BudionAuthError(body or f"HTTP {response.status}")
                    raise BudionApiError(body or f"HTTP {response.status}")

                if response.status == 204:
                    return None

                return await response.json()
        except ClientResponseError as err:
            raise BudionApiError(str(err)) from err

    async def login(self, email: str, password: str) -> str:
        """Log in and return an API token."""
        data = await self._request(
            "POST",
            "auth/login",
            auth=False,
            json={
                "email": email,
                "password": password,
                "device_name": DEVICE_NAME,
            },
        )
        assert isinstance(data, dict)

        if data.get("two_factor"):
            raise BudionTwoFactorRequired(data["challenge_token"])

        token = data.get("token")
        if not token:
            raise BudionAuthError("No token returned")

        self._token = token
        return token

    async def complete_two_factor(
        self,
        challenge_token: str,
        code: str,
        *,
        recovery: bool = False,
    ) -> str:
        """Complete two-factor login and return an API token."""
        payload: dict[str, Any] = {"challenge_token": challenge_token}
        if recovery:
            payload["recovery_code"] = code
        else:
            payload["code"] = code

        data = await self._request(
            "POST",
            "auth/two-factor",
            auth=False,
            json=payload,
        )
        assert isinstance(data, dict)

        token = data.get("token")
        if not token:
            raise BudionAuthError("No token returned")

        self._token = token
        return token

    async def validate_token(self) -> dict[str, Any]:
        """Validate the current token by fetching the user profile."""
        data = await self._request("GET", "auth/user")
        assert isinstance(data, dict)
        return data.get("user", data.get("data", data))

    async def get_families(self) -> list[dict[str, Any]]:
        """Return all families for the authenticated user."""
        data = await self._request("GET", "families")
        if isinstance(data, dict):
            return data.get("data", [])
        return data or []

    async def get_family(self, family_id: int) -> dict[str, Any]:
        """Return a single family."""
        data = await self._request("GET", f"families/{family_id}")
        assert isinstance(data, dict)
        return data.get("data", data)

    async def get_meal_plan(
        self,
        family_id: int,
        *,
        from_date: str,
        to_date: str,
    ) -> dict[str, Any]:
        """Return meal plan entries for a date range."""
        data = await self._request(
            "GET",
            f"families/{family_id}/meal-plan",
            params={"from": from_date, "to": to_date},
        )
        assert isinstance(data, dict)
        return data

    async def get_shopping_lists(self, family_id: int) -> list[dict[str, Any]]:
        """Return shopping lists for a family."""
        data = await self._request("GET", f"families/{family_id}/shopping-lists")
        if isinstance(data, dict):
            return data.get("data", [])
        return data or []

    async def get_tasks_today(
        self,
        family_id: int,
        *,
        include_overdue: bool = True,
    ) -> dict[str, Any]:
        """Return today's tasks for a family."""
        params = {"include_overdue": "1"} if include_overdue else {}
        data = await self._request(
            "GET",
            f"families/{family_id}/tasks/today",
            params=params,
        )
        assert isinstance(data, dict)
        return data

    async def get_contacts(self, family_id: int) -> list[dict[str, Any]]:
        """Return contacts for a family."""
        data = await self._request("GET", f"families/{family_id}/contacts")
        if isinstance(data, dict):
            return data.get("data", [])
        return data or []

    async def get_members(self, family_id: int) -> list[dict[str, Any]]:
        """Return family members."""
        data = await self._request("GET", f"families/{family_id}/members")
        if isinstance(data, dict):
            return data.get("data", [])
        return data or []
