from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_BRAND, CONF_ENTITY_NAME, CONF_POSTAL_CODE, DOMAIN
from .feed import (
    MatchResult,
    RegieEssenceApi,
    RegieEssenceApiError,
    build_entry_title,
    find_station_matches,
    selector_unique_id,
)


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): str,
        vol.Optional(CONF_ADDRESS, default=""): str,
        vol.Optional(CONF_POSTAL_CODE, default=""): str,
        vol.Optional(CONF_BRAND, default=""): str,
        vol.Optional(CONF_ENTITY_NAME, default=""): str,
    }
)


class CannotConnect(Exception):
    """Raised when the integration cannot reach the station feed."""


class InvalidStationSelection(Exception):
    def __init__(self, match_result: MatchResult) -> None:
        self.match_result = match_result


class RegieEssenceQuebecConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        placeholders = {"candidates": ""}

        if user_input is not None:
            cleaned_input = {key: str(value).strip() for key, value in user_input.items()}

            try:
                station = await validate_station_selection(self.hass, cleaned_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidStationSelection as err:
                errors["base"] = err.match_result.error or "invalid_station"
                placeholders["candidates"] = ", ".join(err.match_result.candidates or []) or "none"
            except Exception:
                errors["base"] = "unknown"
            else:
                unique_id = selector_unique_id(
                    cleaned_input[CONF_NAME],
                    cleaned_input[CONF_ADDRESS],
                    cleaned_input[CONF_POSTAL_CODE],
                    cleaned_input[CONF_BRAND],
                )
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=build_entry_title(cleaned_input, station),
                    data=cleaned_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders=placeholders,
        )


async def validate_station_selection(hass, user_input: dict[str, str]):
    api = RegieEssenceApi(async_get_clientsession(hass))
    try:
        snapshot = await api.async_fetch_snapshot()
    except RegieEssenceApiError as err:
        raise CannotConnect from err

    match = find_station_matches(
        snapshot.stations,
        name=user_input.get(CONF_NAME, ""),
        address=user_input.get(CONF_ADDRESS, ""),
        postal_code=user_input.get(CONF_POSTAL_CODE, ""),
        brand=user_input.get(CONF_BRAND, ""),
    )

    if match.station is None:
        raise InvalidStationSelection(match)

    return match.station
