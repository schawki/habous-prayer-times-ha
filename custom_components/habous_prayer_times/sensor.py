"""Capteurs : six horaires + prochaine prière pour chaque lieu suivi."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_point_in_time, async_track_time_change
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import ADHAN_PRAYERS, DOMAIN, NEXT_PRAYER_HOLD_SECONDS, PRAYERS, SRC_LABEL_LOCAL
from .coordinator import HabousCoordinator
from .timeutil import diff_minutes


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: HabousCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []
    for place_id in coordinator.data["places"]:
        entities.extend(PrayerSensor(coordinator, place_id, p) for p in PRAYERS)
        entities.append(NextPrayerSensor(coordinator, place_id))
    async_add_entities(entities)


class _PlaceSensor(CoordinatorEntity[HabousCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: HabousCoordinator, place_id: str) -> None:
        super().__init__(coordinator)
        self._place_id = place_id
        place = coordinator.data["places"][place_id]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{coordinator.entry.entry_id}_{place_id}")},
            name=f"Prayer times – {place['name']}",
            manufacturer="Morocco prayer times",
        )

    @property
    def _place(self) -> dict[str, Any] | None:
        return self.coordinator.data["places"].get(self._place_id)

    def _times(self, day: date):
        return self.coordinator.times_for(self._place_id, day)

    @property
    def available(self) -> bool:
        return super().available and self._place is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        place = self._place or {}
        found = self._times(dt_util.now().date())
        meta = found[1] if found else {}
        return {
            "place": place.get("label"),
            "entity": self._place_id,
            "habous_city": place.get("city_name"),
            "distance_km": place.get("distance_km"),
            "source": meta.get("source"),
            "last_update": meta.get("updated"),
            "mode": place.get("mode"),
            "calculated_at": (
                place["calculated_at"].isoformat()
                if meta.get("source") == SRC_LABEL_LOCAL and place.get("calculated_at")
                else None
            ),
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        # Le jour change : on réécrit l'état peu après minuit.
        self.async_on_remove(
            async_track_time_change(self.hass, self._midnight, hour=0, minute=0, second=30)
        )

    @callback
    def _midnight(self, _now: datetime) -> None:
        self.async_write_ha_state()


class PrayerSensor(_PlaceSensor):
    def __init__(self, coordinator: HabousCoordinator, place_id: str, prayer: str) -> None:
        super().__init__(coordinator, place_id)
        self._prayer = prayer
        self._attr_translation_key = prayer
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{place_id}_{prayer}"

    @property
    def native_value(self) -> datetime | None:
        found = self._times(dt_util.now().date())
        return found[0][self._prayer] if found else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Ajoute, quand le dépôt couvre le jour : heure Habous, heure calculée, écart."""
        attrs = super().extra_state_attributes
        both = self.coordinator.comparison_for(self._place_id, dt_util.now().date())
        if both:
            repo, calc_time = both["repository"][self._prayer], both["calculated"][self._prayer]
            attrs["repository_time"] = repo.isoformat()
            attrs["calculated_time"] = calc_time.isoformat()
            attrs["difference_min"] = diff_minutes(repo, calc_time)
        return attrs


class NextPrayerSensor(_PlaceSensor):
    """Prochaine prière. Attribut `prayer` : fajr, dhuhr, asr, maghrib ou isha."""

    _attr_translation_key = "next_prayer"

    def __init__(self, coordinator: HabousCoordinator, place_id: str) -> None:
        super().__init__(coordinator, place_id)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{place_id}_next"
        self._unsub = None

    def _next(self) -> tuple[str, datetime] | None:
        now = dt_util.now()
        hold = timedelta(seconds=NEXT_PRAYER_HOLD_SECONDS)
        for offset in (0, 1):
            found = self._times(now.date() + timedelta(days=offset))
            if not found:
                continue
            for prayer in ADHAN_PRAYERS:
                if found[0][prayer] + hold > now:
                    return prayer, found[0][prayer]
        return None

    @property
    def native_value(self) -> datetime | None:
        nxt = self._next()
        return nxt[1] if nxt else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = super().extra_state_attributes
        nxt = self._next()
        attrs["prayer"] = nxt[0] if nxt else None
        return attrs

    @callback
    def _schedule(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None
        if nxt := self._next():
            self._unsub = async_track_point_in_time(
                self.hass, self._fire, nxt[1] + timedelta(seconds=NEXT_PRAYER_HOLD_SECONDS)
            )

    @callback
    def _fire(self, _now: datetime) -> None:
        self._unsub = None
        self.async_write_ha_state()
        self._schedule()

    @callback
    def _handle_coordinator_update(self) -> None:
        super()._handle_coordinator_update()
        self._schedule()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._schedule()
        self.async_on_remove(lambda: self._unsub and self._unsub())
