from __future__ import annotations

from datetime import UTC, datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_BRAND, CONF_ENTITY_NAME, CONF_FUEL_TYPES, CONF_POSTAL_CODE, COORDINATOR, DOMAIN, ENTRY_DATA
from .coordinator import RegieEssenceDataUpdateCoordinator
from .feed import FuelPrice, MatchResult, find_station_matches, selector_unique_id


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    domain_data = hass.data[DOMAIN]
    coordinator: RegieEssenceDataUpdateCoordinator = domain_data[COORDINATOR]
    selector = domain_data[ENTRY_DATA][entry.entry_id]
    entities: list[SensorEntity] = [RegieEssenceQuebecLastProviderUpdateSensor(coordinator, entry, selector)]
    fuel_types = selector.get(CONF_FUEL_TYPES, [])
    if not fuel_types:
        match = _find_match_result(coordinator, selector)
        fuel_types = (
            [{"slug": price.slug, "name": price.gas_type} for price in match.station.prices]
            if match.station is not None
            else []
        )

    entities.extend(
        [
            RegieEssenceQuebecFuelSensor(coordinator, entry, selector, fuel_type["slug"], fuel_type["name"])
            for fuel_type in fuel_types
        ]
    )
    async_add_entities(entities)


class RegieEssenceQuebecBaseSensor(CoordinatorEntity[RegieEssenceDataUpdateCoordinator], SensorEntity):
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
    def _match_result(self) -> MatchResult:
        return _find_match_result(self.coordinator, self._selector)

    @property
    def _snapshot_timestamp(self) -> datetime | None:
        snapshot = self.coordinator.data
        if snapshot is None or not snapshot.generated_at:
            return None
        return _parse_timestamp(snapshot.generated_at)

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

        attributes["provider_last_update"] = snapshot.generated_at

        match = self._match_result
        if match.station is None:
            attributes["match_status"] = match.error or "unknown"
            attributes["match_candidates"] = match.candidates or []
            return attributes

        station = match.station
        attributes.update(
            {
                "match_status": "matched",
                "station_name": station.name,
                "brand": station.brand,
                "status": station.status,
                "address": station.address,
                "postal_code": station.postal_code,
                "region": station.region,
                "latitude": station.latitude,
                "longitude": station.longitude,
            }
        )

        return attributes


class RegieEssenceQuebecLastProviderUpdateSensor(RegieEssenceQuebecBaseSensor):
    _attr_has_entity_name = True
    _attr_name = "Last provider update"
    _attr_icon = "mdi:clock-outline"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self,
        coordinator: RegieEssenceDataUpdateCoordinator,
        entry: ConfigEntry,
        selector: dict[str, str],
    ) -> None:
        super().__init__(coordinator, entry, selector)
        self._attr_unique_id = f"{self._selector_id}_last_provider_update"

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self._snapshot_timestamp is not None

    @property
    def native_value(self) -> datetime | None:
        return self._snapshot_timestamp


class RegieEssenceQuebecFuelSensor(RegieEssenceQuebecBaseSensor):
    _attr_has_entity_name = True
    _attr_icon = "mdi:gas-station"
    _attr_native_unit_of_measurement = "c/L"
    _attr_suggested_display_precision = 1
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: RegieEssenceDataUpdateCoordinator,
        entry: ConfigEntry,
        selector: dict[str, str],
        fuel_slug: str,
        fuel_name: str,
    ) -> None:
        super().__init__(coordinator, entry, selector)
        self._fuel_slug = fuel_slug
        self._fuel_name = fuel_name
        self._attr_unique_id = f"{self._selector_id}_{fuel_slug}"
        self._attr_name = fuel_name

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self._fuel_price is not None

    @property
    def native_value(self) -> float | None:
        fuel_price = self._fuel_price
        return fuel_price.price_cents_per_litre if fuel_price is not None else None

    @property
    def extra_state_attributes(self) -> dict:
        attributes = super().extra_state_attributes
        match = self._match_result
        if match.station is None:
            return attributes

        fuel_price = self._fuel_price
        attributes.update(
            {
                "fuel_type": self._fuel_name,
                "fuel_slug": self._fuel_slug,
                "provider_update_age_minutes": _minutes_since_timestamp(
                    self.coordinator.data.generated_at if self.coordinator.data else ""
                ),
                "raw_price": fuel_price.raw_price if fuel_price else None,
                "available_in_feed": fuel_price.is_available if fuel_price else False,
            }
        )
        return attributes

    @property
    def _fuel_price(self) -> FuelPrice | None:
        match = self._match_result
        if match.station is None:
            return None

        return next(
            (
                price
                for price in match.station.prices
                if price.slug == self._fuel_slug
            ),
            None,
        )


def _find_match_result(
    coordinator: RegieEssenceDataUpdateCoordinator,
    selector: dict[str, str],
) -> MatchResult:
    snapshot = coordinator.data
    if snapshot is None:
        return MatchResult(station=None, error="feed_unavailable", candidates=[])

    return find_station_matches(
        snapshot.stations,
        name=selector.get(CONF_NAME, ""),
        address=selector.get(CONF_ADDRESS, ""),
        postal_code=selector.get(CONF_POSTAL_CODE, ""),
        brand=selector.get(CONF_BRAND, ""),
    )


def _minutes_since_timestamp(value: str) -> int | None:
    timestamp = _parse_timestamp(value)
    if timestamp is None:
        return None

    delta = datetime.now(UTC) - timestamp.astimezone(UTC)
    return max(int(delta.total_seconds() // 60), 0)


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None

    normalized = value.replace("Z", "+00:00")
    try:
        timestamp = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)

    return timestamp
