"""Horaires de prière (Maroc) : dépôt JSON ou calcul local."""

from __future__ import annotations

import shutil
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, SOURCE_REPO
from .coordinator import HabousCoordinator

PLATFORMS = ["sensor", "button"]
_BLUEPRINTS = Path(__file__).parent / "blueprints"


def _install_blueprints(blueprints_root: str) -> None:
    """Copie les blueprints livrés dans <config>/blueprints/automation/habous_prayer_times/.

    Ce dossier appartient à l'intégration : il est réécrit au démarrage pour
    recevoir les mises à jour. Pour personnaliser un blueprint, dupliquez-le
    sous un autre nom.
    """
    if not _BLUEPRINTS.is_dir():
        return
    dest = Path(blueprints_root) / "automation" / DOMAIN
    dest.mkdir(parents=True, exist_ok=True)
    for src in _BLUEPRINTS.glob("*.yaml"):
        target = dest / src.name
        if not target.exists() or target.read_bytes() != src.read_bytes():
            shutil.copyfile(src, target)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await hass.async_add_executor_job(_install_blueprints, hass.config.path("blueprints"))

    coordinator = HabousCoordinator(hass, entry)
    await coordinator.async_load_cache()
    await coordinator.async_config_entry_first_refresh()
    entry.async_on_unload(coordinator.async_start_tracking())

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    platforms = PLATFORMS if coordinator.source == SOURCE_REPO else ["sensor"]
    await hass.config_entries.async_forward_entry_setups(entry, platforms)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator: HabousCoordinator = hass.data[DOMAIN][entry.entry_id]
    platforms = PLATFORMS if coordinator.source == SOURCE_REPO else ["sensor"]
    if unloaded := await hass.config_entries.async_unload_platforms(entry, platforms):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
