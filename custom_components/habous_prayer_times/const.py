"""Constantes de l'intégration Horaires de prière (Maroc)."""

from __future__ import annotations

DOMAIN = "habous_prayer_times"

CONF_SOURCE = "source"
CONF_DATA_URL = "data_url"
CONF_FALLBACK_LOCAL = "fallback_local"
CONF_HOME_CITY = "home_city_id"
CONF_ZONES = "zones"
CONF_PERSONS = "persons"
CONF_FREQUENCY = "update_frequency"
CONF_TUNE_PREFIX = "tune_"  # tune_fajr, tune_sunrise, ... (minutes, calcul local)

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

# Adresse RAW du dossier « data » du dépôt GitHub (source « dépôt de données »).
# Modifiable à tout moment dans les options de l'intégration.
DEFAULT_DATA_URL = (
    "https://raw.githubusercontent.com/schawki/habous-prayer-times-ha/main/data"
)
USER_AGENT = "habous-prayer-times-ha (Home Assistant custom integration)"

# Méthode de la bibliothèque hors ligne : Fajr 19°, Isha 17°.
CALCULATION_METHOD = "morocco"

PRAYERS = ["fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"]
# Prières « avec adhan » (le lever du soleil n'en est pas une).
ADHAN_PRAYERS = ["fajr", "dhuhr", "asr", "maghrib", "isha"]

# Le capteur « Prochaine prière » reste sur la prière atteinte pendant ce délai
# (secondes), pour que les automatisations lisent la bonne prière.
NEXT_PRAYER_HOLD_SECONDS = 60

HOME_ZONE = "zone.home"
CHECK_INTERVAL_HOURS = 1
STORAGE_VERSION = 1

SRC_LABEL_REPO = "repository"
SRC_LABEL_LOCAL = "local_calculation"
