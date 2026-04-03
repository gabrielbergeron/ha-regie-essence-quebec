from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_FUEL_TYPES,
    CONF_UPDATE_INTERVAL_MINUTES,
    COORDINATOR,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    ENTRY_DATA,
    MINIMUM_UPDATE_INTERVAL_MINUTES,
    PLATFORMS,
)
from .coordinator import RegieEssenceDataUpdateCoordinator

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    domain_data = hass.data.setdefault(DOMAIN, {})
    coordinator: RegieEssenceDataUpdateCoordinator | None = domain_data.get(COORDINATOR)

    if coordinator is None:
        coordinator = RegieEssenceDataUpdateCoordinator(hass)
        domain_data[COORDINATOR] = coordinator
    coordinator.update_interval = _effective_update_interval(hass)
    await coordinator.async_refresh()

    entry_data = {
        "name": str(entry.data.get("name", "")),
        "address": str(entry.data.get("address", "")),
        "postal_code": str(entry.data.get("postal_code", "")),
        "brand": str(entry.data.get("brand", "")),
        "entity_name": str(entry.data.get("entity_name", "")),
        "fuel_types": entry.data.get(CONF_FUEL_TYPES, []),
        "update_interval_minutes": int(
            entry.options.get(
                CONF_UPDATE_INTERVAL_MINUTES,
                int(DEFAULT_SCAN_INTERVAL.total_seconds() // 60),
            )
        ),
    }

    domain_data.setdefault(ENTRY_DATA, {})[entry.entry_id] = entry_data
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    domain_data = hass.data.get(DOMAIN, {})
    entries = domain_data.get(ENTRY_DATA, {})
    entries.pop(entry.entry_id, None)

    if not entries:
        domain_data.pop(COORDINATOR, None)
    else:
        coordinator: RegieEssenceDataUpdateCoordinator | None = domain_data.get(COORDINATOR)
        if coordinator is not None:
            coordinator.update_interval = _effective_update_interval(hass)

    return True


def _effective_update_interval(hass: HomeAssistant) -> timedelta:
    entry_intervals = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        configured_minutes = int(
            entry.options.get(
                CONF_UPDATE_INTERVAL_MINUTES,
                int(DEFAULT_SCAN_INTERVAL.total_seconds() // 60),
            )
        )
        entry_intervals.append(max(configured_minutes, MINIMUM_UPDATE_INTERVAL_MINUTES))

    if not entry_intervals:
        return DEFAULT_SCAN_INTERVAL

    return timedelta(minutes=min(entry_intervals))
