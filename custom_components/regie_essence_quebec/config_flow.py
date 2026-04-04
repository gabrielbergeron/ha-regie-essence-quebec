from __future__ import annotations

import math
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlowWithReload
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_BRAND,
    CONF_ENTITY_NAME,
    CONF_FUEL_TYPES,
    CONF_POSTAL_CODE,
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MINIMUM_UPDATE_INTERVAL_MINUTES,
)
from .feed import (
    MatchResult,
    RegieEssenceApi,
    RegieEssenceApiError,
    StationRecord,
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

STEP_LOCATION_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_ENTITY_NAME, default=""): str,
    }
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_UPDATE_INTERVAL_MINUTES): vol.All(
            vol.Coerce(int),
            vol.Range(min=MINIMUM_UPDATE_INTERVAL_MINUTES),
        ),
    }
)


class CannotConnect(Exception):
    """Raised when the integration cannot reach the station feed."""


class InvalidStationSelection(Exception):
    def __init__(self, match_result: MatchResult) -> None:
        self.match_result = match_result


class RegieEssenceQuebecConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._nearest_station: StationRecord | None = None
        self._nearest_distance_km: float | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> "RegieEssenceQuebecOptionsFlow":
        return RegieEssenceQuebecOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        return self.async_show_menu(
            step_id="user",
            menu_options=["manual", "location"],
        )

    async def async_step_manual(self, user_input: dict[str, Any] | None = None):
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
                    data={
                        **cleaned_input,
                        CONF_FUEL_TYPES: [
                            {
                                "slug": price.slug,
                                "name": price.gas_type,
                            }
                            for price in station.prices
                        ],
                    },
                )

        return self.async_show_form(
            step_id="manual",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_location(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if self._nearest_station is None:
            try:
                nearest_station, distance_km = await find_closest_station_to_home(self.hass)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except HomeLocationNotSet:
                errors["base"] = "location_not_set"
            except NoStationCoordinatesAvailable:
                errors["base"] = "no_station_with_coordinates"
            else:
                self._nearest_station = nearest_station
                self._nearest_distance_km = distance_km

        if user_input is not None and self._nearest_station is not None:
            cleaned_entity_name = str(user_input.get(CONF_ENTITY_NAME, "")).strip()
            station = self._nearest_station
            created_data = {
                CONF_NAME: station.name,
                CONF_ADDRESS: station.address,
                CONF_POSTAL_CODE: station.postal_code,
                CONF_BRAND: station.brand,
                CONF_ENTITY_NAME: cleaned_entity_name,
                CONF_FUEL_TYPES: [
                    {
                        "slug": price.slug,
                        "name": price.gas_type,
                    }
                    for price in station.prices
                ],
            }
            unique_id = selector_unique_id(
                station.name,
                station.address,
                station.postal_code,
                station.brand,
            )
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=build_entry_title(created_data, station),
                data=created_data,
            )

        station = self._nearest_station
        placeholders = {
            "name": station.name if station else "",
            "address": station.address if station else "",
            "postal_code": station.postal_code if station else "",
            "brand": station.brand if station and station.brand else "",
            "distance_km": (
                f"{self._nearest_distance_km:.1f}" if self._nearest_distance_km is not None else ""
            ),
        }

        return self.async_show_form(
            step_id="location",
            data_schema=STEP_LOCATION_DATA_SCHEMA,
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


class HomeLocationNotSet(Exception):
    """Raised when Home Assistant has no configured home coordinates."""


class NoStationCoordinatesAvailable(Exception):
    """Raised when no stations with coordinates are available in the feed."""


async def find_closest_station_to_home(hass) -> tuple[StationRecord, float]:
    latitude = hass.config.latitude
    longitude = hass.config.longitude
    if latitude is None or longitude is None:
        raise HomeLocationNotSet

    api = RegieEssenceApi(async_get_clientsession(hass))
    try:
        snapshot = await api.async_fetch_snapshot()
    except RegieEssenceApiError as err:
        raise CannotConnect from err

    station_distances = [
        (station, _distance_km(latitude, longitude, station.latitude, station.longitude))
        for station in snapshot.stations
        if station.latitude is not None and station.longitude is not None
    ]
    if not station_distances:
        raise NoStationCoordinatesAvailable

    return min(station_distances, key=lambda item: item[1])


def _distance_km(
    origin_latitude: float,
    origin_longitude: float,
    station_latitude: float | None,
    station_longitude: float | None,
) -> float:
    if station_latitude is None or station_longitude is None:
        return float("inf")

    radius_km = 6371.0
    latitude_1 = math.radians(origin_latitude)
    longitude_1 = math.radians(origin_longitude)
    latitude_2 = math.radians(station_latitude)
    longitude_2 = math.radians(station_longitude)

    delta_latitude = latitude_2 - latitude_1
    delta_longitude = longitude_2 - longitude_1

    a = (
        math.sin(delta_latitude / 2) ** 2
        + math.cos(latitude_1) * math.cos(latitude_2) * math.sin(delta_longitude / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_km * c


class RegieEssenceQuebecOptionsFlow(OptionsFlowWithReload):
    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            normalized_options = {
                CONF_UPDATE_INTERVAL_MINUTES: max(
                    int(user_input[CONF_UPDATE_INTERVAL_MINUTES]),
                    MINIMUM_UPDATE_INTERVAL_MINUTES,
                )
            }
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                self.hass.config_entries.async_update_entry(entry, options=normalized_options)

            return self.async_create_entry(data=normalized_options)

        default_minutes = int(
            self.config_entry.options.get(
                CONF_UPDATE_INTERVAL_MINUTES,
                int(DEFAULT_SCAN_INTERVAL.total_seconds() // 60),
            )
        )

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA,
                {CONF_UPDATE_INTERVAL_MINUTES: default_minutes},
            ),
        )
