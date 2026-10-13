"""Local calculation of prayer times (no network call).

Uses the offline library `prayer-times-calculator-offline`
(the one used by Home Assistant's "Islamic Prayer Times" integration) with the
"Morocco" method: Fajr 19°, Isha 17°. These times are calculated: they
may differ by a few minutes from the Ministry's official tables.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
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
    """Times of the day (timezone-aware datetimes, in UTC) for some coordinates.

    Coordinates are rounded to ~110 m to limit recalculations when a
    phone moves slightly. `tune`: per-prayer adjustment in minutes.
    """
    tune = tune or {}
    return _compute(
        round(lat, 3),
        round(lon, 3),
        day.isoformat(),
        tuple(int(tune.get(p, 0)) for p in PRAYERS),
    )


def hijri_from_gregorian(day: date, adjust: int = 0) -> dict[str, int] | None:
    """Calculated Hijri date (Umm al-Qura) of a day, shifted by `adjust` days.

    None if the `hijridate` library is missing or the date is outside its range."""
    try:
        from hijridate import Gregorian  # lazy: only needed for calculated dates

        hijri = Gregorian.fromdate(day + timedelta(days=adjust)).to_hijri()
    except (ImportError, ValueError, OverflowError):
        return None
    return {"y": hijri.year, "m": hijri.month, "d": hijri.day}
