from __future__ import annotations

import gzip
import importlib.util
import json
from pathlib import Path
import sys
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "custom_components" / "regie_essence_quebec" / "feed.py"
SPEC = importlib.util.spec_from_file_location("regie_essence_quebec_feed", MODULE_PATH)
FEED_MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None
assert SPEC.loader is not None
sys.modules[SPEC.name] = FEED_MODULE
SPEC.loader.exec_module(FEED_MODULE)

FeedSnapshot = FEED_MODULE.FeedSnapshot
build_entry_title = FEED_MODULE.build_entry_title
choose_primary_price = FEED_MODULE.choose_primary_price
decode_feed_bytes = FEED_MODULE.decode_feed_bytes
find_station_matches = FEED_MODULE.find_station_matches
parse_feed_snapshot = FEED_MODULE.parse_feed_snapshot
parse_price = FEED_MODULE.parse_price


SAMPLE_PAYLOAD = {
    "metadata": {
        "generated_at": "2026-04-03T17:25:06.7157745Z",
    },
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-73.742, 45.558]},
            "properties": {
                "Name": "Costco",
                "brand": "Costco",
                "Status": "En op\u00e9ration",
                "Address": "3002 Boulevard le Carrefour, Laval",
                "PostalCode": "H7T 2P2",
                "Region": "Laval",
                "Prices": [
                    {"GasType": "R\u00e9gulier", "Price": "190.9\u00a2", "IsAvailable": True},
                    {"GasType": "Super", "Price": "215.9\u00a2", "IsAvailable": True},
                ],
            },
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-73.88, 45.67]},
            "properties": {
                "Name": "Couche-Tard",
                "brand": "Ultramar",
                "Status": "En op\u00e9ration",
                "Address": "975 Boulevard Cur\u00e9-Labelle, Blainville",
                "PostalCode": "J7C 2L9",
                "Region": "Laurentides",
                "Prices": [
                    {"GasType": "Diesel", "Price": "168.4\u00a2", "IsAvailable": True},
                ],
            },
        },
    ],
}


class FeedTests(unittest.TestCase):
    def test_parse_price(self) -> None:
        self.assertEqual(parse_price("190.9\u00a2"), 190.9)
        self.assertEqual(parse_price(" 168.4 "), 168.4)
        self.assertIsNone(parse_price(""))

    def test_decode_plain_json_bytes(self) -> None:
        decoded = decode_feed_bytes(json.dumps(SAMPLE_PAYLOAD).encode("utf-8"))
        self.assertEqual(decoded["metadata"]["generated_at"], SAMPLE_PAYLOAD["metadata"]["generated_at"])

    def test_decode_gzip_json_bytes(self) -> None:
        compressed = gzip.compress(json.dumps(SAMPLE_PAYLOAD).encode("utf-8"))
        decoded = decode_feed_bytes(compressed)
        self.assertEqual(len(decoded["features"]), 2)

    def test_parse_feed_snapshot(self) -> None:
        snapshot = parse_feed_snapshot(SAMPLE_PAYLOAD)
        self.assertIsInstance(snapshot, FeedSnapshot)
        self.assertEqual(snapshot.generated_at, "2026-04-03T17:25:06.7157745Z")
        self.assertEqual(snapshot.stations[0].prices[0].slug, "regulier")
        self.assertEqual(snapshot.stations[1].prices[0].price_cents_per_litre, 168.4)

    def test_find_station_with_accent_insensitive_address(self) -> None:
        snapshot = parse_feed_snapshot(SAMPLE_PAYLOAD)
        match = find_station_matches(
            snapshot.stations,
            name="Couche-Tard",
            address="975 Boulevard Cure-Labelle, Blainville",
            postal_code="J7C2L9",
            brand="Ultramar",
        )

        self.assertIsNotNone(match.station)
        self.assertEqual(match.station.postal_code, "J7C 2L9")

    def test_find_station_missing_returns_candidates(self) -> None:
        snapshot = parse_feed_snapshot(SAMPLE_PAYLOAD)
        match = find_station_matches(snapshot.stations, name="Cost")
        self.assertIsNone(match.station)
        self.assertEqual(match.error, "not_found")
        self.assertTrue(match.candidates)

    def test_choose_primary_price_prefers_regular(self) -> None:
        snapshot = parse_feed_snapshot(SAMPLE_PAYLOAD)
        primary_price = choose_primary_price(snapshot.stations[0])
        self.assertIsNotNone(primary_price)
        self.assertEqual(primary_price.gas_type, "R\u00e9gulier")

    def test_build_entry_title_uses_brand_when_helpful(self) -> None:
        snapshot = parse_feed_snapshot(SAMPLE_PAYLOAD)
        title = build_entry_title(
            {
                "name": "Couche-Tard",
                "address": "975 Boulevard Cure-Labelle, Blainville",
                "postal_code": "J7C 2L9",
                "brand": "Ultramar",
                "entity_name": "",
            },
            snapshot.stations[1],
        )
        self.assertEqual(title, "Ultramar - Couche-Tard")


if __name__ == "__main__":
    unittest.main()
