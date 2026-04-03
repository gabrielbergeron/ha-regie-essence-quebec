# HA Regie Essence QC

Home Assistant custom integration for tracking Quebec gas prices from the Regie Essence Quebec public station feed.

This repository now targets HACS and native Home Assistant config entries, not Supervisor add-ons.

## What it does

- Adds one sensor entity per configured gas station
- Stores all gas type prices on that entity as attributes
- Uses the Regie Essence Quebec station feed at `https://regieessencequebec.ca/stations.geojson.gz`
- Shares one feed refresh across all configured stations

## Installation with HACS

1. Add this repository as a custom repository in HACS
2. Choose the repository type `Integration`
3. Install it
4. Restart Home Assistant
5. Go to `Settings -> Devices & Services -> Add Integration`
6. Search for `Regie Essence Quebec`
7. Add one config entry per station you want to track

Before publishing the repository, replace `your-github-user` in [manifest.json](C:\Users\berge\Documents\GIT\HARegieEssenceQC\custom_components\regie_essence_quebec\manifest.json) so the links point at `https://github.com/your-github-user/ha-regie-essence-quebec`.

## Station matching

Each config entry asks for:

- `name` required
- `address` optional but recommended
- `postal_code` optional and strongly recommended when names are common
- `brand` optional
- `entity_name` optional

Matching is accent-insensitive and uses exact comparisons on the fields you provide.
