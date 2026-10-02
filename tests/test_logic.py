"""Tests sans Home Assistant : calcul local, parseur du dépôt, géo, fréquences, blueprints, traductions.

Lancer : python -m unittest discover -s tests -v
Nécessite : pip install prayer-times-calculator-offline pyyaml

NB : la page HTML du test du parseur est SYNTHÉTIQUE (structure supposée) ; elle valide
la logique, pas la compatibilité avec la vraie page des Habous.
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

spec = importlib.util.spec_from_file_location("habous_parser", ROOT / "tools" / "habous_parser.py")
parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser)


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


def synthetic_page(start: date, n: int = 30) -> str:
    rows = []
    for i in range(n):
        d = start + timedelta(days=i)
        rows.append(
            f"<tr><td>{i + 1}</td><td>{d.day}</td><td>jour</td>"
            f"<td>05:{10 + i % 5:02d}</td><td>06:40</td><td>13:35</td>"
            f"<td>17:05</td><td>19:58</td><td>21:12</td></tr>"
        )
    cities = "".join(f'<option value="{i}">Ville {i}</option>' for i in range(1, 15))
    return f"<select name='ville'>{cities}</select><table>{''.join(rows)}</table>"


class ParserTests(unittest.TestCase):
    def test_month_crossing_two_gregorian_months(self):
        out = parser.parse_month(synthetic_page(date(2026, 9, 20)), today=date(2026, 10, 2))
        self.assertEqual(len(out), 30)
        self.assertEqual(out["2026-10-02"]["fajr"], "05:12")
        self.assertEqual(list(out)[0], "2026-09-20")

    def test_inconsistent_page_raises(self):
        html = synthetic_page(date(2026, 9, 20)).replace("<td>3</td><td>22</td>", "<td>3</td><td>9</td>")
        with self.assertRaises(parser.ParseError):
            parser.parse_month(html, today=date(2026, 10, 2))

    def test_garbage_raises(self):
        with self.assertRaises(parser.ParseError):
            parser.parse_month("<html>rien</html>", today=date(2026, 10, 2))


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

        fr = set(keys(json.loads((COMP / "translations" / "fr.json").read_text("utf-8"))))
        en = set(keys(json.loads((COMP / "translations" / "en.json").read_text("utf-8"))))
        self.assertEqual(fr, en)

    def test_option_fields_are_translated(self):
        fr = json.loads((COMP / "translations" / "fr.json").read_text("utf-8"))
        data = fr["options"]["step"]["init"]["data"]
        for key in ("source", "data_url", "fallback_local", "home_city_id", "zones", "persons",
                    "update_frequency", *(f"tune_{p}" for p in const.PRAYERS)):
            self.assertIn(key, data)

    def test_manifest_requires_library(self):
        m = json.loads((COMP / "manifest.json").read_text("utf-8"))
        self.assertTrue(any("prayer-times-calculator-offline" in r for r in m["requirements"]))
        self.assertEqual(list(m)[:0] + sorted(m), sorted(m))


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


if __name__ == "__main__":
    unittest.main()
