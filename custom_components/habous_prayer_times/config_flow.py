"""Configuration : source des horaires, ville du logement, puis options."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import HabousApi, HabousError
from .const import (
    CONF_DATA_URL,
    CONF_FALLBACK_LOCAL,
    CONF_FREQUENCY,
    CONF_HOME_CITY,
    CONF_PERSONS,
    CONF_SOURCE,
    CONF_TUNE_PREFIX,
    CONF_ZONES,
    DEFAULT_DATA_URL,
    DEFAULT_FREQUENCY,
    DEFAULT_SOURCE,
    DOMAIN,
    FREQUENCIES,
    PRAYERS,
    SOURCE_LOCAL,
    SOURCE_REPO,
    SOURCES,
)
from .coordinator import conf
from .geo import nearest_cities


def _home_options(cities: list[dict[str, Any]], hass, count: int = 5) -> list[SelectOptionDict]:
    """Villes les plus proches du logement, avec la distance bien visible."""
    best = nearest_cities(cities, hass.config.latitude, hass.config.longitude, count)
    return [
        SelectOptionDict(
            value=str(c["id"]),
            label=f"{c.get('name_fr') or c.get('name')} — {km:.1f} km",
        )
        for c, km in best
    ]


def _source_selector() -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=SOURCES, translation_key=CONF_SOURCE, mode=SelectSelectorMode.LIST
        )
    )


class HabousConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._base: dict[str, Any] = {}
        self._cities: list[dict[str, Any]] = []

    def _all_persons(self) -> list[str]:
        return [s.entity_id for s in self.hass.states.async_all("person")]

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input[CONF_SOURCE] == SOURCE_LOCAL:
                return self.async_create_entry(
                    title="Prayer times (Morocco)",
                    data=user_input,
                    options={CONF_PERSONS: self._all_persons(), CONF_ZONES: []},
                )
            api = HabousApi(
                async_get_clientsession(self.hass),
                user_input[CONF_DATA_URL],
                self.hass.async_add_executor_job,
            )
            try:
                self._cities = await api.async_get_cities()
            except HabousError:
                errors["base"] = "cannot_connect"
            else:
                if not _home_options(self._cities, self.hass):
                    errors["base"] = "no_geolocated_city"
                else:
                    self._base = user_input
                    return await self.async_step_home()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SOURCE, default=DEFAULT_SOURCE): _source_selector(),
                    vol.Required(CONF_DATA_URL, default=DEFAULT_DATA_URL): str,
                    vol.Required(CONF_FALLBACK_LOCAL, default=True): bool,
                }
            ),
            errors=errors,
        )

    async def async_step_home(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title="Prayer times (Morocco)",
                data={**self._base, CONF_HOME_CITY: user_input[CONF_HOME_CITY]},
                options={CONF_PERSONS: self._all_persons(), CONF_ZONES: []},
            )
        options = _home_options(self._cities, self.hass)
        return self.async_show_form(
            step_id="home",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOME_CITY, default=options[0]["value"]): SelectSelector(
                        SelectSelectorConfig(options=options, mode=SelectSelectorMode.LIST)
                    )
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return HabousOptionsFlow()


class HabousOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self.config_entry
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        coordinator = self.hass.data.get(DOMAIN, {}).get(entry.entry_id)
        cities = coordinator.cities if coordinator else []
        home_opts = _home_options(cities, self.hass, 8) if cities else []

        schema: dict[Any, Any] = {
            vol.Required(CONF_SOURCE, default=conf(entry, CONF_SOURCE, DEFAULT_SOURCE)): _source_selector(),
            vol.Required(CONF_DATA_URL, default=conf(entry, CONF_DATA_URL, DEFAULT_DATA_URL)): str,
            vol.Required(CONF_FALLBACK_LOCAL, default=conf(entry, CONF_FALLBACK_LOCAL, True)): bool,
        }
        if home_opts:
            schema[
                vol.Required(CONF_HOME_CITY, default=str(conf(entry, CONF_HOME_CITY, home_opts[0]["value"])))
            ] = SelectSelector(SelectSelectorConfig(options=home_opts, mode=SelectSelectorMode.LIST))
        schema[vol.Optional(CONF_ZONES, default=conf(entry, CONF_ZONES, []))] = EntitySelector(
            EntitySelectorConfig(domain="zone", multiple=True)
        )
        schema[vol.Optional(CONF_PERSONS, default=conf(entry, CONF_PERSONS, []))] = EntitySelector(
            EntitySelectorConfig(domain="person", multiple=True)
        )
        schema[vol.Required(CONF_FREQUENCY, default=conf(entry, CONF_FREQUENCY, DEFAULT_FREQUENCY))] = (
            SelectSelector(
                SelectSelectorConfig(
                    options=FREQUENCIES,
                    translation_key=CONF_FREQUENCY,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            )
        )
        for prayer in PRAYERS:
            key = f"{CONF_TUNE_PREFIX}{prayer}"
            schema[vol.Optional(key, default=conf(entry, key, 0))] = NumberSelector(
                NumberSelectorConfig(
                    min=-30, max=30, step=1, unit_of_measurement="min", mode=NumberSelectorMode.BOX
                )
            )
        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema))
