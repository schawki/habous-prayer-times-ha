#!/usr/bin/env python3
"""Construit les fichiers JSON (data/) à partir de habous.gov.ma.

Exécuté par le workflow GitHub (.github/workflows/update-data.yml), ou à la main :

    python tools/build_data.py --data-dir data

Principes :
- 1 requête / ville seulement quand le cache couvre moins de --lookahead jours
  (donc ~1 passage complet par mois hijri), avec une pause entre requêtes ;
- géocodage des villes (OpenStreetMap Nominatim, 1 req/s) une seule fois,
  les coordonnées sont ensuite conservées dans data/cities.json ;
- aucune donnée n'est écrite si le parseur lève une erreur (pas d'horaires faux).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPONENT = ROOT / "custom_components" / "habous_prayer_times"
HABOUS_URL = "https://www.habous.gov.ma/prieres/horaire_hijri_2.php"
NOMINATIM = "https://nominatim.openstreetmap.org/search"
UA = "habous-prayer-times-ha/0.1 (data builder; contact via GitHub repository)"
ARABIC = re.compile(r"[؀-ۿ]")


def _load_parser():
    spec = importlib.util.spec_from_file_location("habous_parser", ROOT / "tools" / "habous_parser.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


parser = _load_parser()


def http_get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text("utf-8"))
    except (OSError, ValueError):
        return default


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n", "utf-8")


def geocode(name: str) -> tuple[float, float] | None:
    query = urllib.parse.urlencode({"q": f"{name}, Maroc", "format": "json", "limit": 1})
    try:
        results = json.loads(http_get(f"{NOMINATIM}?{query}"))
    except Exception as err:  # noqa: BLE001
        print(f"  géocodage échoué pour {name}: {err}")
        return None
    time.sleep(1.1)
    if not results:
        return None
    lat, lon = float(results[0]["lat"]), float(results[0]["lon"])
    # Garde-fou : Maroc, Sahara occidental, Sebta et Melilla.
    if not (20.0 <= lat <= 37.5 and -18.0 <= lon <= 0.0):
        print(f"  coordonnées hors du Maroc pour {name}: {lat},{lon} -> ignorées")
        return None
    return round(lat, 4), round(lon, 4)


def build_cities(data_dir: Path, delay: float) -> list[dict]:
    path = data_dir / "cities.json"
    existing = {int(c["id"]): c for c in read_json(path, {}).get("cities", [])}
    html = http_get(f"{HABOUS_URL}?ville=58")
    time.sleep(delay)
    listed = parser.parse_cities(html)

    cities = []
    for item in listed:
        cid, label = item["id"], item["name"]
        city = existing.get(cid, {"id": cid})
        key = "name_ar" if ARABIC.search(label) else "name_fr"
        city[key] = label
        if city.get("lat") is None:
            coords = geocode(city.get("name_fr") or label)
            if coords:
                city["lat"], city["lon"] = coords
        cities.append(city)
    cities.sort(key=lambda c: c["id"])
    write_json(path, {"updated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "cities": cities})
    # Copie embarquée dans l'intégration (utilisée si le dépôt est injoignable).
    write_json(COMPONENT / "cities.json", {"cities": cities})
    missing = [c["id"] for c in cities if c.get("lat") is None]
    print(f"{len(cities)} villes, {len(missing)} sans coordonnées {missing[:10]}")
    return cities


def build_times(cities: list[dict], data_dir: Path, lookahead: int, delay: float) -> tuple[int, int]:
    today = date.today()
    horizon = (today + timedelta(days=lookahead)).isoformat()
    ok = failed = 0
    for city in cities:
        cid = city["id"]
        path = data_dir / "times" / f"{cid}.json"
        current = read_json(path, {"days": {}})
        days = current.get("days", {})
        if days and max(days) >= horizon:
            continue
        try:
            html = http_get(f"{HABOUS_URL}?ville={cid}")
            fresh = parser.parse_month(html, today)
        except Exception as err:  # noqa: BLE001
            print(f"ville {cid}: ÉCHEC ({err})")
            failed += 1
            time.sleep(delay)
            continue
        days.update(fresh)
        cutoff = (today - timedelta(days=7)).isoformat()
        days = {d: t for d, t in days.items() if d >= cutoff}
        write_json(path, {
            "city_id": cid,
            "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "days": days,
        })
        ok += 1
        time.sleep(delay)
    return ok, failed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=str(ROOT / "data"))
    ap.add_argument("--lookahead", type=int, default=3, help="jours de marge avant re-scraping")
    ap.add_argument("--delay", type=float, default=2.0, help="pause (s) entre deux requêtes Habous")
    args = ap.parse_args()
    data_dir = Path(args.data_dir)

    try:
        cities = build_cities(data_dir, args.delay)
    except Exception as err:  # noqa: BLE001
        print(f"Impossible de construire la liste des villes : {err}")
        return 1
    ok, failed = build_times(cities, data_dir, args.lookahead, args.delay)
    print(f"Horaires : {ok} villes mises à jour, {failed} échecs")
    return 1 if failed and not ok else 0


if __name__ == "__main__":
    sys.exit(main())
