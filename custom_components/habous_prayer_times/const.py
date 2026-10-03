"""Constants for the Prayer times Morocco integration."""

from __future__ import annotations

DOMAIN = "habous_prayer_times"

CONF_SOURCE = "source"
CONF_DATA_URL = "data_url"
CONF_FALLBACK_LOCAL = "fallback_local"
CONF_COMPARE = "compare"
CONF_HOME_CITY = "home_city_id"
CONF_ZONES = "zones"
CONF_PERSONS = "persons"
CONF_FREQUENCY = "update_frequency"
CONF_MAX_CITY_DISTANCE = "max_city_distance_km"
CONF_RECALC_TOLERANCE = "recalc_tolerance_km"
CONF_TUNE_PREFIX = "tune_"  # tune_fajr, tune_sunrise, ... (minutes, calcul local)

# Place outside a known zone: Habous city only if it is within ... km, otherwise calculation.
DEFAULT_MAX_CITY_DISTANCE_KM = 30.0
# The calculation of a free place (person outside any zone) is only redone if it moved more than
# ... km from the point of the last calculation, or if the day changed.
DEFAULT_RECALC_TOLERANCE_KM = 5.0

# Mode of a place: known zone, repository city, or local calculation.
MODE_ZONE = "zone"
MODE_REPOSITORY = "repository"
MODE_CALCULATED = "calculated"

SERVICE_RECALCULATE = "recalculate"

SOURCE_REPO = "repository"
SOURCE_LOCAL = "local"
SOURCES = [SOURCE_REPO, SOURCE_LOCAL]
DEFAULT_SOURCE = SOURCE_REPO

FREQ_MONTHLY = "monthly"
FREQ_WEEKLY = "weekly"
FREQ_DAILY = "daily"
FREQ_MANUAL = "manual"
FREQUENCIES = [FREQ_MONTHLY, FREQ_WEEKLY, FREQ_DAILY, FREQ_MANUAL]
DEFAULT_FREQUENCY = FREQ_MONTHLY

# RAW address of the "data" folder of the GitHub repository ("data repository" source).
# Editable at any time in the integration options.
DEFAULT_DATA_URL = (
    "https://raw.githubusercontent.com/schawki/habous-prayer-times-data/main/data"
)
# Former default addresses (0.1 to 0.3): automatically replaced by the new one.
LEGACY_DATA_URLS = (
    "https://raw.githubusercontent.com/schawki/habous-prayer-times-ha/main/data",
)
USER_AGENT = "habous-prayer-times-ha (Home Assistant custom integration)"

# Default local-calculation adjustments (minutes). Measured on Casablanca from 13/09 to
# 12/10/2026: the calculation is within ±1 min of the Habous, except sunrise (+3 to +4 min).
DEFAULT_TUNE = {"sunrise": -3}

# Offline library method: Fajr 19°, Isha 17°.
CALCULATION_METHOD = "morocco"

PRAYERS = ["fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"]
# Prayers "with adhan" (sunrise is not one).
ADHAN_PRAYERS = ["fajr", "dhuhr", "asr", "maghrib", "isha"]

# The "Next prayer" sensor stays on the prayer just reached during this delay
# (seconds), so that automations read the right prayer.
NEXT_PRAYER_HOLD_SECONDS = 60

HOME_ZONE = "zone.home"
CHECK_INTERVAL_HOURS = 1
STORAGE_VERSION = 1

SRC_LABEL_REPO = "repository"
SRC_LABEL_LOCAL = "local_calculation"
