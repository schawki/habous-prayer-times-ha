"""Access to the JSON data repository (no scraping on the Home Assistant side)."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from aiohttp import ClientError, ClientSession

from .const import USER_AGENT

_LOGGER = logging.getLogger(__name__)
_TIMEOUT = 20


class HabousError(Exception):
    """Data retrieval error."""


class HabousApi:
    """JSON repository client: cities.json and times/<id>.json."""

    def __init__(self, session: ClientSession, data_url: str) -> None:
        self._session = session
        self._base = data_url.rstrip("/")

    async def _get_text(self, url: str) -> str:
        try:
            async with asyncio.timeout(_TIMEOUT):
                async with self._session.get(url, headers={"User-Agent": USER_AGENT}) as resp:
                    resp.raise_for_status()
                    return await resp.text()
        except (ClientError, TimeoutError) as err:
            raise HabousError(f"{url}: {err}") from err

    async def async_get_cities(self) -> list[dict[str, Any]]:
        """Cities with coordinates, read from the data repository."""
        try:
            cities = json.loads(await self._get_text(f"{self._base}/cities.json"))["cities"]
        except (ValueError, KeyError) as err:
            raise HabousError(f"cities.json invalide: {err}") from err
        if not cities:
            raise HabousError("Liste des villes vide")
        return cities

    async def async_get_times(self, city_id: int) -> dict[str, Any]:
        """Times of one city: {"days", "updated", "utc_offset", "offsets"} (offsets are optional).

        `offsets` maps each day to the legal-time offset (it wins over the file-level `utc_offset`)."""
        try:
            payload = json.loads(await self._get_text(f"{self._base}/times/{city_id}.json"))
            return {
                "days": payload["days"],
                "updated": payload.get("updated"),
                "utc_offset": payload.get("utc_offset"),
                "offsets": payload.get("offsets") or {},
            }
        except (ValueError, KeyError) as err:
            raise HabousError(f"fichier invalide pour la ville {city_id}: {err}") from err
