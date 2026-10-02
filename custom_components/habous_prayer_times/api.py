"""Accès au dépôt de données JSON (aucun scraping côté Home Assistant)."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from aiohttp import ClientError, ClientSession

from .const import USER_AGENT

_LOGGER = logging.getLogger(__name__)
_BUNDLED_CITIES = Path(__file__).parent / "cities.json"
_TIMEOUT = 20


class HabousError(Exception):
    """Erreur de récupération des données."""


class HabousApi:
    """Client du dépôt JSON : cities.json et times/<id>.json."""

    def __init__(self, session: ClientSession, data_url: str, executor=None) -> None:
        self._session = session
        self._base = data_url.rstrip("/")
        self._executor = executor  # hass.async_add_executor_job

    async def _get_text(self, url: str) -> str:
        try:
            async with asyncio.timeout(_TIMEOUT):
                async with self._session.get(url, headers={"User-Agent": USER_AGENT}) as resp:
                    resp.raise_for_status()
                    return await resp.text()
        except (ClientError, TimeoutError) as err:
            raise HabousError(f"{url}: {err}") from err

    async def async_get_cities(self) -> list[dict[str, Any]]:
        """Villes avec coordonnées : dépôt, sinon copie embarquée."""
        try:
            cities = json.loads(await self._get_text(f"{self._base}/cities.json"))["cities"]
            if cities:
                return cities
        except (HabousError, ValueError, KeyError) as err:
            _LOGGER.warning("cities.json indisponible sur le dépôt : %s", err)

        if _BUNDLED_CITIES.exists():
            read = (
                self._executor(_BUNDLED_CITIES.read_text, "utf-8")
                if self._executor
                else asyncio.to_thread(_BUNDLED_CITIES.read_text, "utf-8")
            )
            try:
                cities = json.loads(await read)["cities"]
                if cities:
                    return cities
            except (ValueError, KeyError):
                pass
        raise HabousError("Liste des villes indisponible")

    async def async_get_times(self, city_id: int) -> dict[str, Any]:
        """Horaires d'une ville : {"days": {...}, "updated": iso}."""
        try:
            payload = json.loads(await self._get_text(f"{self._base}/times/{city_id}.json"))
            return {"days": payload["days"], "updated": payload.get("updated")}
        except (ValueError, KeyError) as err:
            raise HabousError(f"fichier invalide pour la ville {city_id}: {err}") from err
