"""Accès au dépôt de données JSON (aucun scraping côté Home Assistant)."""

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
    """Erreur de récupération des données."""


class HabousApi:
    """Client du dépôt JSON : cities.json et times/<id>.json."""

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
        """Villes avec coordonnées, lues dans le dépôt de données."""
        try:
            cities = json.loads(await self._get_text(f"{self._base}/cities.json"))["cities"]
        except (ValueError, KeyError) as err:
            raise HabousError(f"cities.json invalide: {err}") from err
        if not cities:
            raise HabousError("Liste des villes vide")
        return cities

    async def async_get_times(self, city_id: int) -> dict[str, Any]:
        """Horaires d'une ville : {"days", "updated", "utc_offset"} (décalage facultatif)."""
        try:
            payload = json.loads(await self._get_text(f"{self._base}/times/{city_id}.json"))
            return {
                "days": payload["days"],
                "updated": payload.get("updated"),
                "utc_offset": payload.get("utc_offset"),
            }
        except (ValueError, KeyError) as err:
            raise HabousError(f"fichier invalide pour la ville {city_id}: {err}") from err
