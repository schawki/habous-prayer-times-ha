"""Coordinator: tracked places, repository cache, local calculation as fallback."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from . import calc
from .api import HabousApi, HabousError
from .const import (
    CHECK_INTERVAL_HOURS,
    CONF_COMPARE,
    CONF_DATA_URL,
    CONF_FALLBACK_LOCAL,
    CONF_FREQUENCY,
    CONF_HOME_CITY,
    CONF_MAX_CITY_DISTANCE,
    CONF_PERSONS,
    CONF_RECALC_TOLERANCE,
    CONF_SOURCE,
    CONF_TUNE_PREFIX,
    CONF_ZONES,
    DEFAULT_DATA_URL,
    DEFAULT_FREQUENCY,
    DEFAULT_MAX_CITY_DISTANCE_KM,
    DEFAULT_RECALC_TOLERANCE_KM,
    MODE_CALCULATED,
    MODE_REPOSITORY,
    MODE_ZONE,
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
    """Option if set, otherwise the setup data."""
    return entry.options.get(key, entry.data.get(key, default))


def data_url(entry: ConfigEntry) -> str:
    """Data address; the former default address is replaced by the new one."""
    url = str(conf(entry, CONF_DATA_URL, DEFAULT_DATA_URL))
    return DEFAULT_DATA_URL if url.rstrip("/") in LEGACY_DATA_URLS else url


def is_due(frequency: str, last: datetime | None, now: datetime) -> bool:
    """Is a refresh due according to the chosen frequency?"""
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
    """Offset written in the repository file, otherwise the Home Assistant timezone."""
    return tz_from_offset(utc_offset) or dt_util.get_default_time_zone()


def _at(day_iso: str, hhmm: str, utc_offset: str | None = None) -> datetime:
    d = date.fromisoformat(day_iso)
    h, m = map(int, hhmm.split(":"))
    return datetime(d.year, d.month, d.day, h, m, tzinfo=_tzinfo(utc_offset))


class HabousCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Manage the tracked places (home, zones, people) and their times."""

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
        # Compare with the Habous times (calculated vs published), whichever the source.
        self.compare: bool = bool(conf(entry, CONF_COMPARE, True))
        self.tune = {
            p: int(conf(entry, f"{CONF_TUNE_PREFIX}{p}", DEFAULT_TUNE.get(p, 0))) for p in PRAYERS
        }
        self._store: Store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}")
        self._cache: dict[str, dict[str, Any]] = {}  # city_id(str) -> {"days", "updated"}
        self._last_check: datetime | None = None
        self.cities: list[dict[str, Any]] = []
        self.errors: dict[str, str] = {}
        self._force = False
        # Last calculation of each place: {lat, lon, day, at, free}. Kept in memory.
        self._anchors: dict[str, dict[str, Any]] = {}
        self._forced: set[str] = set()
        self.api = HabousApi(
            async_get_clientsession(hass),
            data_url(entry),
        )

    # ------------------------------------------------------------- lieux
    def _place_coords(self, entity_id: str) -> tuple[float, float, str, str | None] | None:
        """(lat, lon, name, state) of a zone or a person."""
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

    @property
    def uses_repo(self) -> bool:
        """Should the repository be read? Repository source, or comparison with the Habous times."""
        return self.source == SOURCE_REPO or self.compare

    def _choose_city(
        self, entity_id: str, lat: float, lon: float, by_id: dict[int, dict[str, Any]],
        max_km: float,
    ) -> tuple[dict[str, Any] | None, float | None, bool]:
        """(Habous city, distance, calculation_required) of a point, according to the source."""
        if not self.uses_repo or not self.cities:
            return None, None, False
        chosen = conf(self.entry, CONF_HOME_CITY)
        if entity_id == HOME_ZONE and chosen:
            city = by_id.get(int(chosen))
            if city and city.get("lat") is not None:
                return city, haversine_km(lat, lon, city["lat"], city["lon"]), False
        best = nearest_cities(self.cities, lat, lon, 1)
        if best and best[0][1] <= max_km:
            return best[0][0], best[0][1], False
        # No Habous city within range: calculate at the place's position.
        return None, None, True

    def _anchor(
        self, info: dict[str, Any], entity_id: str, lat: float, lon: float, free: bool,
        tolerance_km: float, now: datetime,
    ) -> None:
        """Point and time of the last calculation. Reused as long as the place has not moved more
        than `tolerance_km` (free place) and the day has not changed."""
        if entity_id in self._forced:
            self._anchors.pop(entity_id, None)
        anchor = self._anchors.get(entity_id)
        reuse = False
        if anchor and anchor["day"] == now.date() and anchor["free"] == free:
            if free:
                reuse = haversine_km(anchor["lat"], anchor["lon"], lat, lon) <= tolerance_km
            else:
                reuse = anchor["lat"] == lat and anchor["lon"] == lon
        if not reuse:
            anchor = {"lat": lat, "lon": lon, "day": now.date(), "at": now, "free": free}
            self._anchors[entity_id] = anchor
        info["calc_lat"], info["calc_lon"] = anchor["lat"], anchor["lon"]
        info["calculated_at"] = anchor["at"]

    @staticmethod
    def _zone_of(state: str | None, zones: dict[str, dict[str, Any]]) -> str | None:
        """Known zone where a person is (from the state of its entity), otherwise None."""
        if not state or state in ("not_home", "unknown", "unavailable"):
            return None
        if state == "home":
            return HOME_ZONE if HOME_ZONE in zones else None
        for zone_id, info in zones.items():
            if info["name"].casefold() == state.casefold():
                return zone_id
        return None

    def resolve_places(self) -> dict[str, dict[str, Any]]:
        """place -> {name, kind, mode, label, lat, lon, calc_lat, calc_lon, calculated_at,
        city_id, city_name, distance_km, force_calc}.

        Zones : ville Habous (celle choisie pour le logement, sinon la plus proche dans le
        the configured radius) or calculation. People: times of the known zone they are in;
        otherwise a Habous city within the configured radius; otherwise calculation at their position.
        """
        by_id = {int(c["id"]): c for c in self.cities}
        max_km = float(conf(self.entry, CONF_MAX_CITY_DISTANCE, DEFAULT_MAX_CITY_DISTANCE_KM))
        tol_km = float(conf(self.entry, CONF_RECALC_TOLERANCE, DEFAULT_RECALC_TOLERANCE_KM))
        now = dt_util.now()

        places: dict[str, dict[str, Any]] = {}
        zones: dict[str, dict[str, Any]] = {}
        for entity_id in dict.fromkeys([HOME_ZONE, *conf(self.entry, CONF_ZONES, [])]):
            coords = self._place_coords(entity_id)
            if coords is None:
                continue
            lat, lon, name, state = coords
            city, dist, force_calc = self._choose_city(entity_id, lat, lon, by_id, max_km)
            info = self._new_info(name, "zone", lat, lon, city, dist, force_calc, MODE_ZONE)
            self._anchor(info, entity_id, lat, lon, False, tol_km, now)
            info["label"] = self._label("zone", name, state, info)
            places[entity_id] = zones[entity_id] = info

        for entity_id in dict.fromkeys(conf(self.entry, CONF_PERSONS, [])):
            if entity_id in places:
                continue
            coords = self._place_coords(entity_id)
            if coords is None:
                continue
            lat, lon, name, state = coords
            zone_id = self._zone_of(state, zones)
            if zone_id:
                z = zones[zone_id]
                info = {**z, "name": name, "kind": "person", "lat": lat, "lon": lon, "mode": MODE_ZONE}
                self._anchor(info, entity_id, z["lat"], z["lon"], False, tol_km, now)
            else:
                city, dist, force_calc = self._choose_city(entity_id, lat, lon, by_id, max_km)
                # Local source: the Habous city is only used for comparison, times are calculated.
                mode = MODE_REPOSITORY if city and self.source == SOURCE_REPO else MODE_CALCULATED
                info = self._new_info(name, "person", lat, lon, city, dist, force_calc, mode)
                self._anchor(info, entity_id, lat, lon, True, tol_km, now)
            info["label"] = self._label("person", name, state, info)
            places[entity_id] = info

        self._forced.clear()
        return places

    def _new_info(
        self, name: str, kind: str, lat: float, lon: float, city: dict[str, Any] | None,
        dist: float | None, force_calc: bool, mode: str,
    ) -> dict[str, Any]:
        return {
            "name": name,
            "kind": kind,
            "mode": mode,
            "lat": lat,
            "lon": lon,
            "city_id": int(city["id"]) if city else None,
            "city_name": (city.get("name_fr") or city.get("name")) if city else None,
            "distance_km": None if dist is None else round(dist, 1),
            "force_calc": force_calc,
        }

    def _label(self, kind: str, name: str, state: str | None, info: dict[str, Any]) -> str:
        """Human-readable text of the place (used in notifications)."""
        if kind == "zone":
            return name
        if state == "home":
            home = self.hass.states.get(HOME_ZONE)
            return home.attributes.get("friendly_name", "Home") if home else "Home"
        if state and state != "not_home":
            return state  # name of the zone where the person is
        return info["city_name"] or f"{info['lat']:.2f}, {info['lon']:.2f}"

    # ------------------------------------------------------------ horaires
    def _repository_times(
        self, place: dict[str, Any], day: date
    ) -> tuple[dict[str, datetime], dict[str, Any]] | None:
        """Repository times (cache) for the place's city, if they cover this day."""
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
        """Times of a place for one day + metadata (source, update)."""
        place = (self.data or {}).get("places", {}).get(place_id)
        if not place:
            return None
        if (
            self.source == SOURCE_REPO
            and not place.get("force_calc")
            and (found := self._repository_times(place, day))
        ):
            return found
        if self.source == SOURCE_LOCAL or self.fallback_local or place.get("force_calc"):
            return (
                calc.compute_day(place["calc_lat"], place["calc_lon"], day, self.tune),
                {"source": SRC_LABEL_LOCAL, "updated": None},
            )
        return None

    def comparison_for(self, place_id: str, day: date) -> dict[str, dict[str, datetime]] | None:
        """Repository AND calculated times (with adjustments), to compare them.

        None if either is missing (comparison disabled, day absent from the repository…).
        """
        place = (self.data or {}).get("places", {}).get(place_id)
        if not place or not self.compare or place.get("force_calc"):
            return None
        found = self._repository_times(place, day)
        if not found:
            return None
        return {
            "repository": found[0],
            "calculated": calc.compute_day(place["calc_lat"], place["calc_lon"], day, self.tune),
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
        """Recalculate places when a tracked person moves, and at midnight."""
        persons = conf(self.entry, CONF_PERSONS, [])

        @callback
        def _refresh(*_args: Any) -> None:
            self.hass.async_create_task(self.async_request_refresh())

        unsubs = [async_track_time_change(self.hass, _refresh, hour=0, minute=0, second=10)]
        if persons:
            unsubs.append(async_track_state_change_event(self.hass, persons, _refresh))

        @callback
        def _unsub() -> None:
            for unsub in unsubs:
                unsub()

        return _unsub

    async def async_recalculate(self, entity_id: str | None = None, force: bool = False) -> dict[str, Any]:
        """\"recalculate\" service: recalculate one place (or all) if out of date."""
        places = (self.data or {}).get("places", {})
        targets = [entity_id] if entity_id else list(places)
        if entity_id and entity_id not in places:
            raise ServiceValidationError(f"Lieu inconnu : {entity_id}")
        before = {t: places[t].get("calculated_at") for t in targets}
        if force:
            self._forced.update(targets)
        await self.async_refresh()
        places = (self.data or {}).get("places", {})
        result: dict[str, Any] = {}
        for t in targets:
            at = (places.get(t) or {}).get("calculated_at")
            result[t] = {
                "recalculated": at is not None and at != before[t],
                "calculated_at": at.isoformat() if at else None,
            }
        return result

    # ------------------------------------------------------------- refresh
    async def async_force_refresh(self) -> None:
        """\"Update\" button."""
        self._force = True
        await self.async_refresh()

    async def _async_update_data(self) -> dict[str, Any]:
        now = dt_util.now()
        today = now.date()
        force, self._force = self._force, False

        if self.uses_repo:
            await self._async_refresh_repo(now, today, force)
        places = self.resolve_places()
        if not places:
            raise UpdateFailed("No tracked place has coordinates")
        return {"places": places}

    async def _async_refresh_repo(self, now: datetime, today: date, force: bool) -> None:
        if not self.cities or force:
            try:
                self.cities = await self.api.async_get_cities()
            except HabousError as err:
                if not self.cities and not self.fallback_local and self.source == SOURCE_REPO:
                    raise UpdateFailed(str(err)) from err
                _LOGGER.warning("Liste des villes indisponible : %s", err)
                return

        frequency = conf(self.entry, CONF_FREQUENCY, DEFAULT_FREQUENCY)
        due = force or is_due(frequency, self._last_check, now)
        fetched_any = False
        for city_id in {p["city_id"] for p in self.resolve_places().values() if p["city_id"]}:
            key = str(city_id)
            cached = self._cache.get(key)
            # Even in manual mode: fetch if the current day is missing
            # (new place, outdated file).
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
            if due:  # if everything failed, retry at the next hour
                self._last_check = now
            await self._async_save()
        elif self.errors and not self.fallback_local and not self._cache and self.source == SOURCE_REPO:
            raise UpdateFailed("No prayer-time data available")
