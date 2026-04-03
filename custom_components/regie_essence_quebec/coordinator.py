from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL
from .feed import FeedSnapshot, RegieEssenceApi, RegieEssenceApiError


LOGGER = logging.getLogger(__name__)


class RegieEssenceDataUpdateCoordinator(DataUpdateCoordinator[FeedSnapshot]):
    def __init__(self, hass: HomeAssistant) -> None:
        self.api = RegieEssenceApi(async_get_clientsession(hass))
        super().__init__(
            hass,
            LOGGER,
            name="Regie Essence Quebec",
            update_interval=DEFAULT_SCAN_INTERVAL,
            always_update=False,
        )

    async def _async_update_data(self) -> FeedSnapshot:
        try:
            return await self.api.async_fetch_snapshot()
        except RegieEssenceApiError as err:
            raise UpdateFailed(str(err)) from err
