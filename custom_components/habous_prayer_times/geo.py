"""Calculs géographiques (aucune donnée ne quitte l'instance Home Assistant)."""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt
from typing import Any


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance à vol d'oiseau en kilomètres."""
    p1, p2 = radians(lat1), radians(lat2)
    dphi = p2 - p1
    dlmb = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(p1) * cos(p2) * sin(dlmb / 2) ** 2
    return 2 * 6371.0088 * asin(sqrt(a))


def nearest_cities(
    cities: list[dict[str, Any]], lat: float, lon: float, count: int = 1
) -> list[tuple[dict[str, Any], float]]:
    """Retourne les `count` villes géolocalisées les plus proches, avec distance."""
    scored = [
        (c, haversine_km(lat, lon, c["lat"], c["lon"]))
        for c in cities
        if c.get("lat") is not None and c.get("lon") is not None
    ]
    scored.sort(key=lambda item: item[1])
    return scored[:count]
