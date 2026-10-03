"""Coordinateur : lieux suivis, cache du dépôt, calcul local en repli."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from . import calc
from .api import HabousApi, HabousError
from .const import (
    CHECK_INTERVAL_HOURS,
    CONF_DATA_URL,
    CONF_FALLBACK_LOCAL,
    CONF_FREQUENCY,
    CONF_HOME_CITY,
    CONF_PERSONS,
    CONF_SOURCE,
    CONF_TUNE_PREFIX,
    CONF_ZONES,
    DEFAULT_DATA_URL,
    DEFAULT_FREQUENCY,
    DEFAULT_SOURCE,
    DEFAULT_TUNE,
    DOMAIN,
    FREQ_DAILY,
    FREQ_MANUAL,
    FREQ_MONTHLY,
    FREQ_WEEKLY,
    HOME_ZONE,
    LEGACY_DATA_URLS,
    PRAYERS,
    SOURCE_LOCAL,
    SOURCE_REPO,
    SRC_LABEL_LOCAL,
    SRC_LABEL_REPO,
    STORAGE_VERSION,
)
from .geo import haversine_km, nearest_cities
from .timeutil import tz_from_offset

_LOGGER = logging.getLogger(__name__)


def conf(entry: ConfigEntry, key: str, default: Any = None) -> Any:
    """Option si définie, sinon donnée d'installation."""
    return entry.options.get(key, entry.data.get(key, default))


def data_url(entry: ConfigEntry) -> str:
    """Adresse des données ; l'ancienne adresse par défaut est remplacée par la nouvelle."""
    url = str(conf(entry, CONF_DATA_URL, DEFAULT_DATA_URL))
    return DEFAULT_DATA_URL if url.rstrip("/") in LEGACY_DATA_URLS else url


def is_due(frequency: str, last: datetime | None, now: datetime) -> bool:
    """Faut-il rafraîchir selon la fréquence choisie ?"""
    if last is None:
        return True
    if frequency == FREQ_MANUAL:
        return False
    if frequency == FREQ_DAILY:
        return last.date() != now.date()
    if frequency == FREQ_WEEKLY:
        return last.isocalendar()[:2] != now.isocalendar()[:2]
    if frequency == FREQ_MONTHLY:
        return (last.year, last.month) != (now.year, now.month)
    return False


def _tzinfo(utc_offset: str | None):
    """Décalage écrit dans le fichier du dépôt, sinon fuseau de Home Assistant."""
    return tz_from_offset(utc_offset) or dt_util.get_default_time_zone()


def _at(day_iso: str, hhmm: str, utc_offset: str | None = None) -> datetime:
    d = date.fromisoformat(day_iso)
    h, m = map(int, hhmm.split(":"))
    return datetime(d.year, d.month, d.day, h, m, tzinfo=_tzinfo(utc_offset))


class HabousCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Gère les lieux suivis (logement, zones, personnes) et leurs horaires."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(hours=CHECK_INTERVAL_HOURS),
        )
        self.entry = entry
        self.source: str = conf(entry, CONF_SOURCE, DEFAULT_SOURCE)
        self.fallback_local: bool = conf(entry, CONF_FALLBACK_LOCAL, True)
        self.tune = {
            p: int(conf(entry, f"{CONF_TUNE_PREFIX}{p}", DEFAULT_TUNE.get(p, 0))) for p in PRAYERS
        }
        self._store: Store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}")
        self._cache: dict[str, dict[str, Any]] = {}  # city_id(str) -> {"days", "updated"}
        self._last_check: datetime | None = None
        self.cities: list[dict[str, Any]] = []
        self.errors: dict[str, str] = {}
        self._force = False
        self.api = HabousApi(
            async_get_clientsession(hass),
            data_url(entry),
        )

    # ------------------------------------------------------------- lieux
    def _place_coords(self, entity_id: str) -> tuple[float, float, str, str | None] | None:
        """(lat, lon, nom, état) d'une zone ou d'une personne."""
        if entity_id == HOME_ZONE:
            state = self.hass.states.get(HOME_ZONE)
            name = state.attributes.get("friendly_name", "Home") if state else "Home"
            return self.hass.config.latitude, self.hass.config.longitude, name, None
        state = self.hass.states.get(entity_id)
        if not state or state.attributes.get("latitude") is None:
            return None
        return (
            float(state.attributes["latitude"]),
            float(state.attributes["longitude"]),
            state.attributes.get("friendly_name", entity_id),
            state.state,
        )

    def resolve_places(self) -> dict[str, dict[str, Any]]:
        """place -> {name, kind, label, lat, lon, city_id, city_name, distance_km}."""
        by_id = {int(c["id"]): c for c in self.cities}
        wanted = [(HOME_ZONE, "zone")]
        wanted += [(z, "zone") for z in conf(self.entry, CONF_ZONES, [])]
        wanted += [(p, "person") for p in conf(self.entry, CONF_PERSONS, [])]

        places: dict[str, dict[str, Any]] = {}
        for entity_id, kind in dict.fromkeys(wanted):
            coords = self._place_coords(entity_id)
            if coords is None:
                continue
            lat, lon, name, state = coords
            info: dict[str, Any] = {
                "name": name,
                "kind": kind,
                "lat": lat,
                "lon": lon,
                "city_id": None,
                "city_name": None,
                "distance_km": None,
            }
            if self.source == SOURCE_REPO and self.cities:
                city = dist = None
                chosen = conf(self.entry, CONF_HOME_CITY)
                if entity_id == HOME_ZONE and chosen:
                    city = by_id.get(int(chosen))
                    if city and city.get("lat") is not None:
                        dist = haversine_km(lat, lon, city["lat"], city["lon"])
                else:
                    best = nearest_cities(self.cities, lat, lon, 1)
                    if best:
                        city, dist = best[0]
                if city:
                    info["city_id"] = int(city["id"])
                    info["city_name"] = city.get("name_fr") or city.get("name")
                    info["distance_km"] = None if dist is None else round(dist, 1)
            info["label"] = self._label(kind, name, state, info)
            places[entity_id] = info
        return places

    def _label(self, kind: str, name: str, state: str | None, info: dict[str, Any]) -> str:
        """Texte lisible du lieu (utilisé dans les notifications)."""
        if kind == "zone":
            return name
        if state == "home":
            home = self.hass.states.get(HOME_ZONE)
            return home.attributes.get("friendly_name", "Home") if home else "Home"
        if state and state != "not_home":
            return state  # nom de la zone où se trouve la personne
        return info["city_name"] or f"{info['lat']:.2f}, {info['lon']:.2f}"

    # ------------------------------------------------------------ horaires
    def _repository_times(
        self, place: dict[str, Any], day: date
    ) -> tuple[dict[str, datetime], dict[str, Any]] | None:
        """Horaires du dépôt (cache) pour la ville du lieu, s'ils couvrent ce jour."""
        if place["city_id"] is None:
            return None
        cached = self._cache.get(str(place["city_id"]))
        if not cached or day.isoformat() not in cached["days"]:
            return None
        raw = cached["days"][day.isoformat()]
        offset = cached.get("utc_offset")
        return (
            {p: _at(day.isoformat(), raw[p], offset) for p in PRAYERS},
            {"source": SRC_LABEL_REPO, "updated": cached.get("updated")},
        )

    def times_for(
        self, place_id: str, day: date
    ) -> tuple[dict[str, datetime], dict[str, Any]] | None:
        """Horaires d'un lieu pour un jour + métadonnées (source, mise à jour)."""
        place = (self.data or {}).get("places", {}).get(place_id)
        if not place:
            return None
        if self.source == SOURCE_REPO and (found := self._repository_times(place, day)):
            return found
        if self.source == SOURCE_LOCAL or self.fallback_local:
            return (
                calc.compute_day(place["lat"], place["lon"], day, self.tune),
                {"source": SRC_LABEL_LOCAL, "updated": None},
            )
        return None

    def comparison_for(self, place_id: str, day: date) -> dict[str, dict[str, datetime]] | None:
        """Heures du dépôt ET du calcul (avec ajustements), pour les comparer.

        None si l'une des deux manque (source locale, jour absent du dépôt…).
        """
        place = (self.data or {}).get("places", {}).get(place_id)
        if not place or self.source != SOURCE_REPO:
            return None
        found = self._repository_times(place, day)
        if not found:
            return None
        return {
            "repository": found[0],
            "calculated": calc.compute_day(place["lat"], place["lon"], day, self.tune),
        }

    # --------------------------------------------------------------- cache
    async def async_load_cache(self) -> None:
        stored = await self._store.async_load() or {}
        self._cache = stored.get("cities", {})
        if (raw := stored.get("last_check")) is not None:
            self._last_check = dt_util.parse_datetime(raw)

    async def _async_save(self) -> None:
        await self._store.async_save(
            {
                "cities": self._cache,
                "last_check": self._last_check.isoformat() if self._last_check else None,
            }
        )

    # ------------------------------------------------------ personnes suivies
    @callback
    def async_start_tracking(self):
        """Recalcule les lieux quand une personne suivie se déplace."""
        persons = conf(self.entry, CONF_PERSONS, [])
        if not persons:
            return lambda: None

        @callback
        def _moved(_event: Event) -> None:
            self.hass.async_create_task(self.async_request_refresh())

        return async_track_state_change_event(self.hass, persons, _moved)

    # ----------------------------------------------------------- rafraîchir
    async def async_force_refresh(self) -> None:
        """Bouton « Mettre à jour »."""
        self._force = True
        await self.async_refresh()

    async def _async_update_data(self) -> dict[str, Any]:
        now = dt_util.now()
        today = now.date()
        force, self._force = self._force, False

        if self.source == SOURCE_REPO:
            await self._async_refresh_repo(now, today, force)
        places = self.resolve_places()
        if not places:
            raise UpdateFailed("Aucun lieu suivi n'a de coordonnées")
        return {"places": places}

    async def _async_refresh_repo(self, now: datetime, today: date, force: bool) -> None:
        if not self.cities or force:
            try:
                self.cities = await self.api.async_get_cities()
            except HabousError as err:
                if not self.cities and not self.fallback_local:
                    raise UpdateFailed(str(err)) from err
                _LOGGER.warning("Liste des villes indisponible : %s", err)
                return

        frequency = conf(self.entry, CONF_FREQUENCY, DEFAULT_FREQUENCY)
        due = force or is_due(frequency, self._last_check, now)
        fetched_any = False
        for city_id in {p["city_id"] for p in self.resolve_places().values() if p["city_id"]}:
            key = str(city_id)
            cached = self._cache.get(key)
            # Même en mode manuel : on récupère si le jour courant manque
            # (nouveau lieu, fichier périmé).
            missing_today = not cached or today.isoformat() not in cached["days"]
            if not (due or missing_today):
                continue
            try:
                self._cache[key] = await self.api.async_get_times(city_id)
                self.errors.pop(key, None)
                fetched_any = True
            except HabousError as err:
                self.errors[key] = str(err)
                _LOGGER.warning("Ville %s : %s", city_id, err)

        if fetched_any:
            if due:  # si tout a échoué, on retente à l'heure suivante
                self._last_check = now
            await self._async_save()
        elif self.errors and not self.fallback_local and not self._cache:
            raise UpdateFailed("Aucune donnée d'horaires disponible")
