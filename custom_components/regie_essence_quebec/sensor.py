from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_BRAND, CONF_ENTITY_NAME, CONF_POSTAL_CODE, COORDINATOR, DOMAIN, ENTRY_DATA
from .coordinator import RegieEssenceDataUpdateCoordinator
from .feed import MatchResult, choose_primary_price, find_station_matches, selector_unique_id


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    domain_data = hass.data[DOMAIN]
    coordinator: RegieEssenceDataUpdateCoordinator = domain_data[COORDINATOR]
    selector = domain_data[ENTRY_DATA][entry.entry_id]
    async_add_entities([RegieEssenceQuebecStationSensor(coordinator, entry, selector)])


class RegieEssenceQuebecStationSensor(CoordinatorEntity[RegieEssenceDataUpdateCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:gas-station"
    _attr_name = "Prices"
    _attr_native_unit_of_measurement = "c/L"
    _attr_suggested_display_precision = 1

    def __init__(
        self,
        coordinator: RegieEssenceDataUpdateCoordinator,
        entry: ConfigEntry,
        selector: dict[str, str],
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._selector = selector
        self._station_title = entry.title
        self._selector_id = selector_unique_id(
            selector.get(CONF_NAME, ""),
            selector.get(CONF_ADDRESS, ""),
            selector.get(CONF_POSTAL_CODE, ""),
            selector.get(CONF_BRAND, ""),
        )
        self._attr_unique_id = f"{self._selector_id}_prices"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._selector_id)},
            name=self._station_title,
            manufacturer="Regie Essence Quebec",
            model="Station price feed",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def native_value(self) -> float | None:
        match = self._match_result
        if match.station is None:
            return None

        primary_price = choose_primary_price(match.station)
        return primary_price.price_cents_per_litre if primary_price else None

    @property
    def extra_state_attributes(self) -> dict:
        attributes = {
            "configured_name": self._selector.get(CONF_NAME, ""),
            "configured_address": self._selector.get(CONF_ADDRESS, ""),
            "configured_postal_code": self._selector.get(CONF_POSTAL_CODE, ""),
            "configured_brand": self._selector.get(CONF_BRAND, ""),
            "configured_entity_name": self._selector.get(CONF_ENTITY_NAME, ""),
        }

        snapshot = self.coordinator.data
        if snapshot is None:
            return attributes

        attributes["generated_at"] = snapshot.generated_at

        match = self._match_result
        if match.station is None:
            attributes["match_status"] = match.error or "unknown"
            attributes["match_candidates"] = match.candidates or []
            return attributes

        station = match.station
        primary_price = choose_primary_price(station)
        attributes.update(
            {
                "match_status": "matched",
                "state_fuel_type": primary_price.gas_type if primary_price else None,
                "station_name": station.name,
                "brand": station.brand,
                "status": station.status,
                "address": station.address,
                "postal_code": station.postal_code,
                "region": station.region,
                "latitude": station.latitude,
                "longitude": station.longitude,
                "prices": {},
            }
        )

        for price in station.prices:
            attributes["prices"][price.slug] = {
                "label": price.gas_type,
                "price_cents_per_litre": price.price_cents_per_litre,
                "raw_price": price.raw_price,
                "available": price.is_available,
            }
            attributes[f"{price.slug}_price_cents_per_litre"] = price.price_cents_per_litre
            attributes[f"{price.slug}_raw_price"] = price.raw_price
            attributes[f"{price.slug}_available"] = price.is_available

        return attributes

    @property
    def _match_result(self) -> MatchResult:
        snapshot = self.coordinator.data
        if snapshot is None:
            return MatchResult(station=None, error="feed_unavailable", candidates=[])

        return find_station_matches(
            snapshot.stations,
            name=self._selector.get(CONF_NAME, ""),
            address=self._selector.get(CONF_ADDRESS, ""),
            postal_code=self._selector.get(CONF_POSTAL_CODE, ""),
            brand=self._selector.get(CONF_BRAND, ""),
        )
