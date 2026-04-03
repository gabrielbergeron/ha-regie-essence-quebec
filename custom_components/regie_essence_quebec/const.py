from __future__ import annotations

from datetime import timedelta

from homeassistant.const import Platform


DOMAIN = "regie_essence_quebec"
PLATFORMS = [Platform.SENSOR]

CONF_BRAND = "brand"
CONF_ENTITY_NAME = "entity_name"
CONF_FUEL_TYPES = "fuel_types"
CONF_POSTAL_CODE = "postal_code"
CONF_UPDATE_INTERVAL_MINUTES = "update_interval_minutes"

FEED_URL = "https://regieessencequebec.ca/stations.geojson.gz"
DEFAULT_SCAN_INTERVAL = timedelta(minutes=5)
MINIMUM_UPDATE_INTERVAL_MINUTES = 5

COORDINATOR = "coordinator"
ENTRY_DATA = "entry_data"
