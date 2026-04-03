from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import COORDINATOR, DOMAIN, ENTRY_DATA, PLATFORMS
from .coordinator import RegieEssenceDataUpdateCoordinator


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    domain_data = hass.data.setdefault(DOMAIN, {})
    coordinator: RegieEssenceDataUpdateCoordinator | None = domain_data.get(COORDINATOR)

    if coordinator is None:
        coordinator = RegieEssenceDataUpdateCoordinator(hass)
        domain_data[COORDINATOR] = coordinator
        await coordinator.async_refresh()

    entry_data = {
        "name": str(entry.data.get("name", "")),
        "address": str(entry.data.get("address", "")),
        "postal_code": str(entry.data.get("postal_code", "")),
        "brand": str(entry.data.get("brand", "")),
        "entity_name": str(entry.data.get("entity_name", "")),
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

    return True
