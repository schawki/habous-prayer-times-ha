"""Tests sans Home Assistant : calcul local, décalage horaire, géo, fréquences, blueprints, traductions, carte.

Lancer : python -m unittest discover -s tests -v
Nécessite : pip install prayer-times-calculator-offline pyyaml
"""

import importlib
import importlib.util
import json
import sys
import types
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
COMP = ROOT / "custom_components" / "habous_prayer_times"

# Paquet factice : permet d'importer calc/const/geo sans charger Home Assistant.
pkg = types.ModuleType("hp")
pkg.__path__ = [str(COMP)]
sys.modules["hp"] = pkg
calc = importlib.import_module("hp.calc")
geo = importlib.import_module("hp.geo")
const = importlib.import_module("hp.const")
timeutil = importlib.import_module("hp.timeutil")


def local(dt: datetime) -> str:
    """Heure locale marocaine hors Ramadan (UTC+1)."""
    return (dt + timedelta(hours=1)).strftime("%H:%M")


class CalcTests(unittest.TestCase):
    def test_matches_reference_rabat_2026_08_31(self):
        # Référence : horaires d'un site tiers citant les Habous (±1 min sur Asr).
        out = calc.compute_day(34.0209, -6.8416, date(2026, 8, 31))
        got = {p: local(out[p]) for p in const.PRAYERS}
        self.assertEqual(got["fajr"], "05:28")
        self.assertEqual(got["sunrise"], "07:00")
        self.assertEqual(got["dhuhr"], "13:33")
        self.assertEqual(got["maghrib"], "20:00")
        self.assertEqual(got["isha"], "21:16")
        self.assertIn(got["asr"], ("17:05", "17:06"))

    def test_tune_shifts_minutes(self):
        base = calc.compute_day(33.5731, -7.5898, date(2026, 10, 2))
        tuned = calc.compute_day(33.5731, -7.5898, date(2026, 10, 2), {"fajr": -2, "asr": 1})
        self.assertEqual(base["fajr"] - tuned["fajr"], timedelta(minutes=2))
        self.assertEqual(tuned["asr"] - base["asr"], timedelta(minutes=1))
        self.assertEqual(base["isha"], tuned["isha"])

    def test_order_and_awareness(self):
        out = calc.compute_day(31.6295, -7.9811, date(2026, 12, 15))
        times = [out[p] for p in const.PRAYERS]
        self.assertEqual(times, sorted(times))
        self.assertTrue(all(t.tzinfo for t in times))


class TimeUtilTests(unittest.TestCase):
    def test_offsets(self):
        from datetime import timezone
        self.assertEqual(timeutil.tz_from_offset("+00:00").utcoffset(None), timedelta(0))
        self.assertEqual(timeutil.tz_from_offset("+01:00").utcoffset(None), timedelta(hours=1))
        self.assertEqual(timeutil.tz_from_offset("-02:30").utcoffset(None), -timedelta(hours=2, minutes=30))
        for bad in (None, "", "1h", "+1:00", "UTC"):
            self.assertIsNone(timeutil.tz_from_offset(bad))

    def test_json_time_uses_file_offset(self):
        # 12:25 locales à +00:00 = 12:25 UTC ; à +01:00 = 11:25 UTC (la base de HA n'intervient pas)
        d = date(2026, 10, 3)
        utc = lambda off: datetime(d.year, d.month, d.day, 12, 25, tzinfo=timeutil.tz_from_offset(off)).astimezone(
            __import__("datetime").timezone.utc).strftime("%H:%M")
        self.assertEqual(utc("+00:00"), "12:25")
        self.assertEqual(utc("+01:00"), "11:25")

    def test_difference_is_calculated_minus_repository(self):
        repo = datetime(2026, 10, 3, 6, 23, tzinfo=timeutil.tz_from_offset("+00:00"))
        self.assertEqual(timeutil.diff_minutes(repo, repo + timedelta(minutes=3, seconds=10)), 3)
        self.assertEqual(timeutil.diff_minutes(repo, repo - timedelta(minutes=1)), -1)
        self.assertEqual(timeutil.diff_minutes(repo, repo), 0)


class DefaultsTests(unittest.TestCase):
    def test_json_is_default_with_local_fallback(self):
        self.assertEqual(const.DEFAULT_SOURCE, const.SOURCE_REPO)
        self.assertIn("habous-prayer-times-data", const.DEFAULT_DATA_URL)
        self.assertTrue(const.DEFAULT_DATA_URL.endswith("/data"))
        coord = (COMP / "coordinator.py").read_text("utf-8")
        self.assertIn("CONF_FALLBACK_LOCAL, True", coord)

    def test_legacy_data_url_is_replaced(self):
        src = (COMP / "coordinator.py").read_text("utf-8")
        body = src[src.index("def data_url"): src.index("def is_due")]
        ns = {"ConfigEntry": object, "conf": lambda e, k, d=None: e.get(k, d), "CONF_DATA_URL": "data_url",
              "DEFAULT_DATA_URL": const.DEFAULT_DATA_URL, "LEGACY_DATA_URLS": const.LEGACY_DATA_URLS}
        exec("from __future__ import annotations\n" + body, ns)  # noqa: S102
        f = ns["data_url"]
        self.assertEqual(f({"data_url": const.LEGACY_DATA_URLS[0]}), const.DEFAULT_DATA_URL)
        self.assertEqual(f({"data_url": const.LEGACY_DATA_URLS[0] + "/"}), const.DEFAULT_DATA_URL)
        self.assertEqual(f({}), const.DEFAULT_DATA_URL)
        self.assertEqual(f({"data_url": "https://exemple.org/data"}), "https://exemple.org/data")

    def test_sunrise_default_tune(self):
        self.assertEqual(const.DEFAULT_TUNE, {"sunrise": -3})

    def test_repository_offset_is_read_and_comparison_exposed(self):
        api = (COMP / "api.py").read_text("utf-8")
        self.assertIn('"utc_offset"', api)
        self.assertNotIn("_BUNDLED_CITIES", api)
        coord = (COMP / "coordinator.py").read_text("utf-8")
        self.assertIn("def comparison_for", coord)
        sensor = (COMP / "sensor.py").read_text("utf-8")
        for attr in ("repository_time", "calculated_time", "difference_min"):
            self.assertIn(attr, sensor)
        card = (COMP / "frontend" / "habous-prayer-card.js").read_text("utf-8")
        for token in ("show_comparison", "repository_time", "calculated_time", "difference_min"):
            self.assertIn(token, card)

    def test_all_python_modules_parse(self):
        import ast
        for f in COMP.glob("*.py"):
            ast.parse(f.read_text("utf-8"), filename=str(f))


class GeoTests(unittest.TestCase):
    def test_distance_casablanca_rabat(self):
        self.assertAlmostEqual(geo.haversine_km(33.5731, -7.5898, 34.0209, -6.8416), 87, delta=4)

    def test_nearest_skips_ungeolocated(self):
        cities = [
            {"id": 1, "lat": None, "lon": None},
            {"id": 2, "lat": 33.5, "lon": -7.6},
            {"id": 3, "lat": 34.0, "lon": -6.8},
        ]
        best = geo.nearest_cities(cities, 33.57, -7.59, 2)
        self.assertEqual([c["id"] for c, _ in best], [2, 3])


class FrequencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # coordinator.py importe Home Assistant : on extrait seulement is_due.
        src = (COMP / "coordinator.py").read_text("utf-8")
        body = src[src.index("def is_due") : src.index("def _at")]
        ns = {"datetime": datetime, "FREQ_MANUAL": "manual", "FREQ_DAILY": "daily",
              "FREQ_WEEKLY": "weekly", "FREQ_MONTHLY": "monthly"}
        exec("from __future__ import annotations\n" + body, ns)  # noqa: S102
        cls.is_due = staticmethod(ns["is_due"])

    def test_rules(self):
        now = datetime(2026, 10, 2, 12)
        self.assertTrue(self.is_due("monthly", None, now))
        self.assertFalse(self.is_due("monthly", datetime(2026, 10, 1), now))
        self.assertTrue(self.is_due("monthly", datetime(2026, 9, 30), now))
        self.assertFalse(self.is_due("weekly", datetime(2026, 9, 29), now))
        self.assertTrue(self.is_due("weekly", datetime(2026, 9, 27), now))
        self.assertTrue(self.is_due("daily", datetime(2026, 10, 1), now))
        self.assertFalse(self.is_due("manual", datetime(2020, 1, 1), now))


class _Loader(yaml.SafeLoader):
    pass


_Loader.add_constructor("!input", lambda loader, node: f"INPUT:{loader.construct_scalar(node)}")


class BlueprintTests(unittest.TestCase):
    def load(self, name):
        return yaml.load((COMP / "blueprints" / name).read_text("utf-8"), Loader=_Loader)

    def test_inputs_are_all_declared(self):
        for name in ("notify_prayer.yaml", "announce_prayer_music_assistant.yaml"):
            bp = self.load(name)
            declared = set(bp["blueprint"]["input"])
            text = (COMP / "blueprints" / name).read_text("utf-8")
            used = {t.split()[0] for t in text.split("!input ")[1:]}
            self.assertTrue(used <= declared, f"{name}: {used - declared}")
            self.assertEqual(bp["blueprint"]["domain"], "automation")

    def test_notify_lets_user_pick_prayers(self):
        bp = self.load("notify_prayer.yaml")
        prayers = bp["blueprint"]["input"]["prayers"]["selector"]["select"]
        self.assertTrue(prayers["multiple"])
        self.assertEqual([o["value"] for o in prayers["options"]],
                         ["fajr", "dhuhr", "asr", "maghrib", "isha"])
        self.assertTrue(all(not o["value"].startswith("+") for o in
                            bp["blueprint"]["input"]["offset"]["selector"]["select"]["options"]))


class MetaTests(unittest.TestCase):
    def test_translations_have_same_keys(self):
        def keys(d, p=""):
            for k, v in d.items():
                yield from keys(v, f"{p}{k}.") if isinstance(v, dict) else [f"{p}{k}"]

        files = sorted((COMP / "translations").glob("*.json"))
        self.assertGreaterEqual(len(files), 2)
        sets = {f.stem: set(keys(json.loads(f.read_text("utf-8")))) for f in files}
        reference = sets["fr"]
        for lang, found in sets.items():
            self.assertEqual(found, reference, f"{lang}: {found ^ reference}")

    def test_option_fields_are_translated(self):
        fr = json.loads((COMP / "translations" / "fr.json").read_text("utf-8"))
        data = fr["options"]["step"]["init"]["data"]
        for key in ("source", "data_url", "fallback_local", "compare", "home_city_id", "zones", "persons",
                    "update_frequency", *(f"tune_{p}" for p in const.PRAYERS)):
            self.assertIn(key, data)

    def test_manifest_requires_library(self):
        m = json.loads((COMP / "manifest.json").read_text("utf-8"))
        self.assertTrue(any("prayer-times-calculator-offline" in r for r in m["requirements"]))
        self.assertEqual(list(m)[:0] + sorted(m), sorted(m))


class ArabicTests(unittest.TestCase):
    ar = json.loads((COMP / "translations" / "ar.json").read_text("utf-8"))

    def test_prayer_names_follow_french_and_english(self):
        sensors = self.ar["entity"]["sensor"]
        self.assertEqual(
            {k: v["name"] for k, v in sensors.items()},
            {"fajr": "الفجر", "sunrise": "الشروق", "dhuhr": "الظهر", "asr": "العصر",
             "maghrib": "المغرب", "isha": "العشاء", "next_prayer": "الصلاة القادمة"},
        )

    def test_card_has_arabic_and_rtl(self):
        js = (COMP / "frontend" / "habous-prayer-card.js").read_text("utf-8")
        self.assertIn("TEXT.ar", js)
        self.assertIn('"rtl"', js)
        self.assertIn("nu-latn", js)  # chiffres latins
        for ar_word in ("الفجر", "الأوقاف"):
            self.assertIn(ar_word, js)

    def test_blueprint_offers_arabic(self):
        bp = (COMP / "blueprints" / "notify_prayer.yaml").read_text("utf-8")
        self.assertIn("value: ar", bp)
        self.assertIn("حان الآن وقت", bp)
        for f in ("notify_prayer.yaml", "announce_prayer_music_assistant.yaml"):
            self.assertIn("Fajr — الفجر", (COMP / "blueprints" / f).read_text("utf-8"))

    def test_manifest_keys_sorted_like_hassfest(self):
        keys = list(json.loads((COMP / "manifest.json").read_text("utf-8")))
        self.assertEqual(keys[:2], ["domain", "name"])
        self.assertEqual(keys[2:], sorted(keys[2:]))

    def test_version_bumped(self):
        self.assertEqual(json.loads((COMP / "manifest.json").read_text("utf-8"))["version"], "0.6.1")


class CardTests(unittest.TestCase):
    def test_card_shipped_and_registered(self):
        js = (COMP / "frontend" / "habous-prayer-card.js").read_text("utf-8")
        self.assertIn('customElements.define("habous-prayer-card"', js)
        init = (COMP / "__init__.py").read_text("utf-8")
        self.assertIn("add_extra_js_url", init)
        self.assertIn("async_register_static_paths", init)
        m = json.loads((COMP / "manifest.json").read_text("utf-8"))
        self.assertTrue({"frontend", "http"} <= set(m["dependencies"]))

    def test_card_syntax(self):
        import shutil, subprocess
        node = shutil.which("node")
        if not node:
            self.skipTest("node absent")
        r = subprocess.run([node, "--check", str(COMP / "frontend" / "habous-prayer-card.js")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)


class EnglishFirstTests(unittest.TestCase):
    """English is the reference language; French and Arabic are translations."""

    def test_readmes_exist_and_link_each_other(self):
        for name in ("README.md", "README.fr.md", "README.ar.md"):
            text = (ROOT / name).read_text("utf-8")
            for other in ("README.md", "README.fr.md", "README.ar.md"):
                if other != name:
                    self.assertIn(f"]({other})", text, f"{name} must link to {other}")

    def test_translations_have_the_same_keys(self):
        def keys(node, prefix=""):
            out = set()
            for k, v in node.items():
                out |= keys(v, f"{prefix}{k}.") if isinstance(v, dict) else {f"{prefix}{k}"}
            return out
        folder = COMP / "translations"
        ref = keys(json.loads((folder / "en.json").read_text("utf-8")))
        for path in folder.glob("*.json"):
            self.assertEqual(keys(json.loads(path.read_text("utf-8"))), ref, path.name)

    def test_notify_blueprint_uses_sensor_utc_offset(self):
        text = (COMP / "blueprints" / "notify_prayer.yaml").read_text("utf-8")
        self.assertIn("state_attr(sensor, 'utc_offset')", text)

    def test_names_are_english(self):
        for path in (COMP / "manifest.json", ROOT / "hacs.json"):
            self.assertEqual(json.loads(path.read_text("utf-8"))["name"], "Prayer times Morocco")
        for path in (COMP / "blueprints").glob("*.yaml"):
            head = path.read_text("utf-8").split("input:")[0]
            self.assertNotIn(" / ", head.split("description")[0], path.name)


class CompactSeparatorTests(unittest.TestCase):
    def test_every_card_language_defines_hm_separator(self):
        js = (COMP / "frontend" / "habous-prayer-card.js").read_text("utf-8")
        self.assertEqual(js.count("hm_sep:"), 3)
        self.assertIn('hm_sep: ":"', js)
        self.assertIn("${t.hm_sep}", js)


if __name__ == "__main__":
    unittest.main()
