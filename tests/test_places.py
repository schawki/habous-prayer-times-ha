"""Règles de choix des horaires (zone connue / ville Habous / calcul) et recalcul avec tolérance.

Home Assistant est remplacé par de petits faux modules : seule la logique du coordinateur est testée.
Lancer : python -m unittest discover -s tests -v
"""

import asyncio
import importlib
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMP = ROOT / "custom_components" / "habous_prayer_times"


def _module(name: str, **attrs) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__dict__.update(attrs)
    sys.modules[name] = mod
    return mod


class _Generic:
    def __class_getitem__(cls, _item):
        return cls


class _Coordinator(_Generic):
    def __init__(self, hass, logger, **kwargs):
        self.hass = hass
        self.data = None

    async def async_refresh(self):
        self.data = await self._async_update_data()

    async def async_request_refresh(self):
        await self.async_refresh()


class _Err(Exception):
    pass


_NOW = {"value": datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)}


def _install_stubs():
    try:
        import aiohttp  # noqa: F401
    except ImportError:
        _module("aiohttp", ClientError=Exception, ClientSession=object)
    _module("homeassistant")
    _module("homeassistant.config_entries", ConfigEntry=object)
    _module("homeassistant.core", HomeAssistant=object, callback=lambda f: f)
    _module("homeassistant.exceptions", ServiceValidationError=_Err)
    _module("homeassistant.helpers")
    _module("homeassistant.helpers.aiohttp_client", async_get_clientsession=lambda hass: None)
    _module(
        "homeassistant.helpers.event",
        async_track_state_change_event=lambda *a, **k: (lambda: None),
        async_track_time_change=lambda *a, **k: (lambda: None),
    )
    _module("homeassistant.helpers.storage", Store=lambda *a, **k: None)
    _module(
        "homeassistant.helpers.update_coordinator",
        DataUpdateCoordinator=_Coordinator,
        UpdateFailed=_Err,
    )
    util = _module("homeassistant.util")
    dt = _module(
        "homeassistant.util.dt",
        now=lambda: _NOW["value"],
        get_default_time_zone=lambda: timezone.utc,
        parse_datetime=datetime.fromisoformat,
    )
    util.dt = dt


_install_stubs()
pkg = types.ModuleType("hq")
pkg.__path__ = [str(COMP)]
sys.modules["hq"] = pkg
const = importlib.import_module("hq.const")
coordinator_mod = importlib.import_module("hq.coordinator")

CASA = {"id": 58, "lat": 33.5945, "lon": -7.62, "name_ar": "الدار البيضاء", "name_fr": "Casablanca"}
RABAT = {"id": 3, "lat": 34.0209, "lon": -6.8416, "name_fr": "Rabat"}
BROKEN = {"id": 30, "name_ar": "بوسكور"}  # sans coordonnées : ignorée


class _State:
    def __init__(self, state, **attributes):
        self.state = state
        self.attributes = attributes


class _States:
    def __init__(self):
        self.items = {}

    def get(self, entity_id):
        return self.items.get(entity_id)


class _Entry:
    def __init__(self, data=None, options=None):
        self.data = data or {}
        self.options = options or {}
        self.entry_id = "e1"


def make(options=None, data=None, persons=(), zones=()):
    hass = types.SimpleNamespace(
        states=_States(), config=types.SimpleNamespace(latitude=33.5731, longitude=-7.5898)
    )
    hass.states.items["zone.home"] = _State("0", friendly_name="Maison", latitude=33.5731, longitude=-7.5898)
    opts = {"persons": list(persons), "zones": list(zones), **(options or {})}
    coord = coordinator_mod.HabousCoordinator(hass, _Entry(data or {"home_city_id": "58"}, opts))
    coord.cities = [CASA, RABAT, BROKEN]
    return hass, coord


def person(hass, name, state, lat, lon):
    hass.states.items[f"person.{name}"] = _State(state, friendly_name=name.title(), latitude=lat, longitude=lon)


class ChoiceTests(unittest.TestCase):
    def setUp(self):
        _NOW["value"] = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)

    def test_home_uses_chosen_city_even_if_far(self):
        hass, coord = make(data={"home_city_id": "3"})
        home = coord.resolve_places()["zone.home"]
        self.assertEqual(home["city_id"], 3)
        self.assertEqual(home["mode"], "zone")

    def test_person_in_home_zone_gets_the_zone_city(self):
        hass, coord = make(data={"home_city_id": "3"}, persons=["person.saad"])
        person(hass, "saad", "home", 33.60, -7.60)  # plus proche de Casablanca que de Rabat
        info = coord.resolve_places()["person.saad"]
        self.assertEqual(info["city_id"], 3)  # celle de la zone, pas la plus proche de la personne
        self.assertEqual(info["mode"], "zone")
        self.assertEqual((info["calc_lat"], info["calc_lon"]), (33.5731, -7.5898))  # point de la zone

    def test_person_in_extra_zone(self):
        hass, coord = make(persons=["person.saad"], zones=["zone.work"])
        hass.states.items["zone.work"] = _State("0", friendly_name="Bureau", latitude=34.02, longitude=-6.84)
        person(hass, "saad", "Bureau", 34.0201, -6.8401)
        info = coord.resolve_places()["person.saad"]
        self.assertEqual(info["city_id"], 3)
        self.assertEqual(info["mode"], "zone")

    def test_person_outside_zone_near_a_city_uses_repository(self):
        hass, coord = make(persons=["person.saad"])
        person(hass, "saad", "not_home", 34.00, -6.85)  # ~3 km de Rabat
        info = coord.resolve_places()["person.saad"]
        self.assertEqual((info["city_id"], info["mode"], info["force_calc"]), (3, "repository", False))

    def test_person_far_from_any_city_is_calculated(self):
        hass, coord = make(persons=["person.saad"])
        person(hass, "saad", "not_home", 48.85, 2.35)  # Paris
        info = coord.resolve_places()["person.saad"]
        self.assertEqual((info["city_id"], info["mode"], info["force_calc"]), (None, "calculated", True))
        self.assertIsNotNone(info["calculated_at"])

    def test_max_distance_is_adjustable(self):
        hass, coord = make(persons=["person.saad"], options={"max_city_distance_km": 1})
        person(hass, "saad", "not_home", 34.00, -6.85)  # ~3 km de Rabat > 1 km
        self.assertEqual(coord.resolve_places()["person.saad"]["mode"], "calculated")

    def test_local_source_calculates_free_people(self):
        hass, coord = make(persons=["person.saad"], options={"source": "local"})
        person(hass, "saad", "not_home", 34.00, -6.85)
        info = coord.resolve_places()["person.saad"]
        self.assertEqual((info["city_id"], info["mode"]), (None, "calculated"))

    def test_times_come_from_the_anchor_point(self):
        hass, coord = make(persons=["person.saad"])
        person(hass, "saad", "not_home", 48.85, 2.35)
        coord.data = {"places": coord.resolve_places()}
        found = coord.times_for("person.saad", _NOW["value"].date())
        self.assertEqual(found[1]["source"], const.SRC_LABEL_LOCAL)  # calcul, même sans « fallback »


class RecalcTests(unittest.TestCase):
    def setUp(self):
        _NOW["value"] = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)
        self.hass, self.coord = make(persons=["person.saad"], options={"recalc_tolerance_km": 5})
        person(self.hass, "saad", "not_home", 48.85, 2.35)
        self.first = self.coord.resolve_places()["person.saad"]

    def _again(self, lat, lon, minutes=30, days=0):
        _NOW["value"] += timedelta(minutes=minutes, days=days)
        person(self.hass, "saad", "not_home", lat, lon)
        return self.coord.resolve_places()["person.saad"]

    def test_small_move_keeps_calculation(self):
        info = self._again(48.86, 2.36)  # ~1,4 km
        self.assertEqual(info["calculated_at"], self.first["calculated_at"])
        self.assertEqual((info["calc_lat"], info["calc_lon"]), (48.85, 2.35))

    def test_big_move_recalculates(self):
        info = self._again(48.95, 2.45)  # ~13 km
        self.assertGreater(info["calculated_at"], self.first["calculated_at"])
        self.assertEqual((info["calc_lat"], info["calc_lon"]), (48.95, 2.45))

    def test_tolerance_is_adjustable(self):
        _, coord = make(persons=["person.saad"], options={"recalc_tolerance_km": 0.5})
        person(_, "saad", "not_home", 48.85, 2.35)
        a = coord.resolve_places()["person.saad"]
        person(_, "saad", "not_home", 48.86, 2.36)  # ~1,4 km > 0,5
        b = coord.resolve_places()["person.saad"]
        self.assertEqual(b["calc_lat"], 48.86)
        self.assertEqual(a["calc_lat"], 48.85)

    def test_new_day_recalculates(self):
        info = self._again(48.85, 2.35, days=1)
        self.assertGreater(info["calculated_at"], self.first["calculated_at"])

    def test_service_respects_tolerance_and_force(self):
        self.coord.data = {"places": self.coord.resolve_places()}

        async def go():
            return (
                await self.coord.async_recalculate("person.saad"),
                await self.coord.async_recalculate("person.saad", force=True),
            )

        _NOW["value"] += timedelta(minutes=10)
        plain, forced = asyncio.run(go())
        self.assertFalse(plain["person.saad"]["recalculated"])
        self.assertTrue(forced["person.saad"]["recalculated"])

    def test_unknown_place_is_rejected(self):
        self.coord.data = {"places": self.coord.resolve_places()}
        with self.assertRaises(Exception):
            asyncio.run(self.coord.async_recalculate("person.nobody"))

    def test_leaving_a_zone_starts_a_fresh_calculation(self):
        hass, coord = make(persons=["person.saad"])
        person(hass, "saad", "home", 33.5731, -7.5898)
        coord.resolve_places()
        _NOW["value"] += timedelta(minutes=5)
        person(hass, "saad", "not_home", 48.85, 2.35)
        info = coord.resolve_places()["person.saad"]
        self.assertEqual((info["calc_lat"], info["calc_lon"]), (48.85, 2.35))


if __name__ == "__main__":
    unittest.main()
