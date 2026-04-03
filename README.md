# HA Régie Essence QC

[English](./README.md) | [Français](./README.fr.md)

[![GitHub Release][releases-shield]][releases]
[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]

Home Assistant custom integration for tracking Quebec gas prices from the public [Régie Essence Québec](https://regieessencequebec.ca/) station feed.

This integration creates one device per configured station and one sensor per available fuel type. Multiple stations can be added through the Home Assistant UI, while a shared coordinator keeps feed refreshes efficient.

## Features

- Native Home Assistant integration with config flow
- HACS-compatible repository structure
- One device per configured gas station
- One sensor entity per available fuel type for each configured station
- Shared polling of the Régie Essence Québec feed for all configured stations
- Configurable refresh interval with a minimum of 5 minutes
- Support for multiple tracked stations

## Installation via HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=gabrielbergeron&repository=ha-regie-essence-quebec)

1. Follow the HACS custom repository guide [here](https://hacs.xyz/docs/faq/custom_repositories/).
2. Add the repository URL: `https://github.com/gabrielbergeron/ha-regie-essence-quebec`
3. Select the category type `Integration`
4. Install the integration from HACS
5. Restart Home Assistant
6. Go to `Settings -> Devices & Services`
7. Click `+ Add Integration` and search for `Régie Essence Québec`

## Configuration

Each configured entry represents one station. You can add as many stations as you want.

For each station, the integration creates separate sensors for the fuel types returned by the feed, for example `Regulier`, `Super`, or `Diesel`.

The config flow supports these fields:

- `name` required
- `address` optional but recommended
- `postal_code` optional and strongly recommended when station names are common
- `brand` optional
- `entity_name` optional

After a station is added, you can open the integration options to change the refresh interval. The minimum allowed value is 5 minutes.

The refresh interval is global for the whole integration. Changing it from any configured station applies the same value to all configured stations.

## Station Matching

Station matching is accent-insensitive and uses exact comparisons on the values you provide.

For the best results:

- Use the exact station name from the Régie Essence Québec feed
- Add `address` when the station name is common
- Add `postal_code` to disambiguate nearby stations with similar names
- Add `brand` when a station name appears under multiple banners

If a station cannot be matched exactly, the integration will show an error during setup and provide candidate matches when possible.

## Data Source

Data is fetched from the official Régie Essence Québec feed:

`https://regieessencequebec.ca/stations.geojson.gz`

The upstream dataset is updated approximately every 5 minutes.

Each fuel sensor also exposes provider update metadata in its attributes, including the last provider timestamp and the number of minutes since the upstream feed was updated.

[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Gabriel%20Bergeron-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/gabrielbergeron/ha-regie-essence-quebec.svg?style=for-the-badge
[releases]: https://github.com/gabrielbergeron/ha-regie-essence-quebec/releases
