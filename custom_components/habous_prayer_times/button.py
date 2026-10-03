"""\"Update\" button (fetch the times immediately)."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import HabousCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([UpdateButton(hass.data[DOMAIN][entry.entry_id])])


class UpdateButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "update"

    def __init__(self, coordinator: HabousCoordinator) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{coordinator.entry.entry_id}_update"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name="Prayer times (Habous)",
            manufacturer="Ministry of Habous and Islamic Affairs",
        )

    async def async_press(self) -> None:
        await self._coordinator.async_force_refresh()
