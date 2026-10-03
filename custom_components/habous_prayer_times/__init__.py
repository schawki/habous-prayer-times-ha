"""Prayer times (Morocco): JSON data repository or local calculation."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
import voluptuous as vol

from .const import DOMAIN, SERVICE_RECALCULATE, SOURCE_REPO
from .coordinator import HabousCoordinator

PLATFORMS = ["sensor", "button"]
_BLUEPRINTS = Path(__file__).parent / "blueprints"
_FRONTEND = Path(__file__).parent / "frontend"
CARD_FILE = "habous-prayer-card.js"
CARD_URL = f"/{DOMAIN}/{CARD_FILE}"
_CARD_FLAG = f"{DOMAIN}_card_registered"


def _install_blueprints(blueprints_root: str) -> None:
    """Copy the bundled blueprints to <config>/blueprints/automation/habous_prayer_times/.

    This folder belongs to the integration: it is rewritten at startup to
    receive updates. To customise a blueprint, duplicate it
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


def _manifest_version() -> str:
    return json.loads((Path(__file__).parent / "manifest.json").read_text("utf-8"))["version"]


async def _register_card(hass: HomeAssistant) -> None:
    """Serve the bundled Lovelace card and load it automatically in the UI."""
    if hass.data.get(_CARD_FLAG):
        return
    hass.data[_CARD_FLAG] = True
    version = await hass.async_add_executor_job(_manifest_version)
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(_FRONTEND / CARD_FILE), cache_headers=False)]
    )
    add_extra_js_url(hass, f"{CARD_URL}?v={version}")


def _register_service(hass: HomeAssistant) -> None:
    """Service habous_prayer_times.recalculate: recalculate a place if it is out of date."""
    if hass.services.has_service(DOMAIN, SERVICE_RECALCULATE):
        return

    async def _recalculate(call: ServiceCall) -> ServiceResponse:
        coordinators = list(hass.data.get(DOMAIN, {}).values())
        if not coordinators:
            raise ServiceValidationError("Integration not configured")
        entity_id = call.data.get("entity_id")
        result: dict = {}
        found = False
        for coordinator in coordinators:
            places = (coordinator.data or {}).get("places", {})
            if entity_id and entity_id not in places:
                continue
            found = True
            result.update(await coordinator.async_recalculate(entity_id, call.data["force"]))
        if entity_id and not found:
            raise ServiceValidationError(f"Lieu inconnu : {entity_id}")
        return {"places": result}

    hass.services.async_register(
        DOMAIN,
        SERVICE_RECALCULATE,
        _recalculate,
        schema=vol.Schema({vol.Optional("entity_id"): str, vol.Optional("force", default=False): bool}),
        supports_response=SupportsResponse.OPTIONAL,
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _register_service(hass)
    await hass.async_add_executor_job(_install_blueprints, hass.config.path("blueprints"))
    await _register_card(hass)

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
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_RECALCULATE)
    return unloaded
