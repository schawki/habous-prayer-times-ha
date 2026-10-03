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
CONF_MAX_CITY_DISTANCE = "max_city_distance_km"
CONF_RECALC_TOLERANCE = "recalc_tolerance_km"
CONF_TUNE_PREFIX = "tune_"  # tune_fajr, tune_sunrise, ... (minutes, calcul local)

# Lieu hors zone connue : ville Habous seulement si elle est à moins de ... km, sinon calcul.
DEFAULT_MAX_CITY_DISTANCE_KM = 30.0
# Le calcul d'un lieu libre (personne hors zone) n'est refait que si elle s'est éloignée de
# plus de ... km du point du dernier calcul, ou si le jour a changé.
DEFAULT_RECALC_TOLERANCE_KM = 5.0

# Mode d'un lieu : zone connue, ville du dépôt, ou calcul local.
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

# Adresse RAW du dossier « data » du dépôt GitHub (source « dépôt de données »).
# Modifiable à tout moment dans les options de l'intégration.
DEFAULT_DATA_URL = (
    "https://raw.githubusercontent.com/schawki/habous-prayer-times-data/main/data"
)
# Anciennes adresses par défaut (0.1 à 0.3) : remplacées automatiquement par la nouvelle.
LEGACY_DATA_URLS = (
    "https://raw.githubusercontent.com/schawki/habous-prayer-times-ha/main/data",
)
USER_AGENT = "habous-prayer-times-ha (Home Assistant custom integration)"

# Ajustements par défaut du calcul local (minutes). Mesuré sur Casablanca du 13/09 au
# 12/10/2026 : le calcul est à ±1 min des Habous, sauf le Chourouk (+3 à +4 min).
DEFAULT_TUNE = {"sunrise": -3}

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
