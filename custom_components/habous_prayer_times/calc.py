"""Calcul local des horaires de prière (aucun appel réseau).

Utilise la bibliothèque hors ligne `prayer-times-calculator-offline`
(celle de l'intégration « Islamic Prayer Times » de Home Assistant) avec la
méthode « Morocco » : Fajr 19°, Isha 17°. Ces horaires sont calculés : ils
peuvent différer de quelques minutes des tableaux officiels du Ministère.
"""

from __future__ import annotations

from datetime import date, datetime
from functools import lru_cache

from .const import CALCULATION_METHOD, PRAYERS

_LIB_KEYS = {
    "fajr": "Fajr",
    "sunrise": "Sunrise",
    "dhuhr": "Dhuhr",
    "asr": "Asr",
    "maghrib": "Maghrib",
    "isha": "Isha",
}


@lru_cache(maxsize=512)
def _compute(lat: float, lon: float, day_iso: str, tune: tuple[int, ...]) -> dict[str, datetime]:
    from prayer_times_calculator_offline import PrayerTimesCalculator  # import tardif

    t = dict(zip(PRAYERS, tune))
    raw = PrayerTimesCalculator(
        latitude=lat,
        longitude=lon,
        calculation_method=CALCULATION_METHOD,
        date=day_iso,
        tune=any(tune),
        fajr_tune=t["fajr"],
        sunrise_tune=t["sunrise"],
        dhuhr_tune=t["dhuhr"],
        asr_tune=t["asr"],
        maghrib_tune=t["maghrib"],
        isha_tune=t["isha"],
    ).fetch_prayer_times()
    return {p: datetime.fromisoformat(raw[_LIB_KEYS[p]]) for p in PRAYERS}


def compute_day(
    lat: float, lon: float, day: date, tune: dict[str, int] | None = None
) -> dict[str, datetime]:
    """Horaires du jour (datetimes avec fuseau, en UTC) pour des coordonnées.

    Coordonnées arrondies à ~110 m pour limiter les recalculs quand un
    téléphone bouge un peu. `tune` : ajustement en minutes par prière.
    """
    tune = tune or {}
    return _compute(
        round(lat, 3),
        round(lon, 3),
        day.isoformat(),
        tuple(int(tune.get(p, 0)) for p in PRAYERS),
    )
