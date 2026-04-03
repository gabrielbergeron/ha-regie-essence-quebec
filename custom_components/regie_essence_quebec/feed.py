from __future__ import annotations

import gzip
import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import aiohttp

FEED_URL = "https://regieessencequebec.ca/stations.geojson.gz"

class RegieEssenceApiError(Exception):
    """Raised when the Regie Essence feed cannot be fetched or parsed."""


@dataclass(slots=True)
class FuelPrice:
    gas_type: str
    slug: str
    price_cents_per_litre: float | None
    raw_price: str
    is_available: bool


@dataclass(slots=True)
class StationRecord:
    name: str
    address: str
    postal_code: str
    brand: str
    status: str
    region: str
    latitude: float | None
    longitude: float | None
    prices: list[FuelPrice]


@dataclass(slots=True)
class FeedSnapshot:
    generated_at: str
    stations: list[StationRecord]


@dataclass(slots=True)
class MatchResult:
    station: StationRecord | None
    error: str | None = None
    candidates: list[str] | None = None


class RegieEssenceApi:
    def __init__(self, session) -> None:
        self._session = session

    async def async_fetch_snapshot(self) -> FeedSnapshot:
        import aiohttp

        try:
            async with self._session.get(FEED_URL, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response.raise_for_status()
                payload = await response.read()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise RegieEssenceApiError(f"Unable to fetch station feed: {err}") from err

        try:
            decoded = decode_feed_bytes(payload)
            return parse_feed_snapshot(decoded)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as err:
            raise RegieEssenceApiError(f"Unable to parse station feed: {err}") from err


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    ascii_text = ascii_text.lower()
    ascii_text = re.sub(r"[^a-z0-9]+", " ", ascii_text)
    return re.sub(r"\s+", " ", ascii_text).strip()


def normalize_postal_code(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "", value or "").upper()


def slugify(value: str) -> str:
    slug = normalize_text(value).replace(" ", "_")
    return slug or "station"


def selector_unique_id(name: str, address: str, postal_code: str, brand: str) -> str:
    signature = "|".join(
        [
            normalize_text(name),
            normalize_text(address),
            normalize_postal_code(postal_code),
            normalize_text(brand),
        ]
    )
    return hashlib.sha1(signature.encode("utf-8")).hexdigest()[:12]


def parse_price(value: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)", value or "")
    return float(match.group(1)) if match else None


def decode_feed_bytes(raw_bytes: bytes) -> dict[str, Any]:
    body = gzip.decompress(raw_bytes) if raw_bytes[:2] == b"\x1f\x8b" else raw_bytes
    return json.loads(body.decode("utf-8"))


def parse_feed_snapshot(payload: dict[str, Any]) -> FeedSnapshot:
    metadata = payload.get("metadata") or {}
    features = payload.get("features") or []
    stations: list[StationRecord] = []

    for feature in features:
        properties = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or [None, None]

        prices = [
            FuelPrice(
                gas_type=str(item.get("GasType") or "").strip(),
                slug=slugify(str(item.get("GasType") or "")),
                price_cents_per_litre=parse_price(str(item.get("Price") or "")),
                raw_price=str(item.get("Price") or "").strip(),
                is_available=bool(item.get("IsAvailable")),
            )
            for item in properties.get("Prices") or []
        ]

        stations.append(
            StationRecord(
                name=str(properties.get("Name") or "").strip(),
                address=str(properties.get("Address") or "").strip(),
                postal_code=str(properties.get("PostalCode") or "").strip(),
                brand=str(properties.get("brand") or "").strip(),
                status=str(properties.get("Status") or "").strip(),
                region=str(properties.get("Region") or "").strip(),
                longitude=float(coordinates[0]) if coordinates[0] is not None else None,
                latitude=float(coordinates[1]) if coordinates[1] is not None else None,
                prices=prices,
            )
        )

    return FeedSnapshot(
        generated_at=str(metadata.get("generated_at") or ""),
        stations=stations,
    )


def find_station_matches(
    stations: list[StationRecord],
    *,
    name: str,
    address: str = "",
    postal_code: str = "",
    brand: str = "",
) -> MatchResult:
    normalized_name = normalize_text(name)
    normalized_address = normalize_text(address)
    normalized_postal_code = normalize_postal_code(postal_code)
    normalized_brand = normalize_text(brand)

    candidates = [
        station
        for station in stations
        if normalize_text(station.name) == normalized_name
    ]

    if address:
        candidates = [
            station
            for station in candidates
            if normalize_text(station.address) == normalized_address
        ]

    if postal_code:
        candidates = [
            station
            for station in candidates
            if normalize_postal_code(station.postal_code) == normalized_postal_code
        ]

    if brand:
        candidates = [
            station
            for station in candidates
            if normalize_text(station.brand) == normalized_brand
        ]

    if len(candidates) == 1:
        return MatchResult(station=candidates[0])

    if len(candidates) > 1:
        return MatchResult(
            station=None,
            error="ambiguous",
            candidates=[format_station_candidate(station) for station in candidates[:5]],
        )

    fuzzy_candidates = [
        station
        for station in stations
        if normalized_name and normalized_name in normalize_text(station.name)
    ]

    return MatchResult(
        station=None,
        error="not_found",
        candidates=[format_station_candidate(station) for station in fuzzy_candidates[:5]],
    )


def format_station_candidate(station: StationRecord) -> str:
    parts = [station.name]
    if station.brand and normalize_text(station.brand) not in normalize_text(station.name):
        parts.append(f"brand={station.brand}")
    if station.address:
        parts.append(f"address={station.address}")
    if station.postal_code:
        parts.append(f"postal_code={station.postal_code}")
    return ", ".join(parts)


def choose_primary_price(station: StationRecord) -> FuelPrice | None:
    regular = next(
        (
            price
            for price in station.prices
            if price.slug == "regulier"
            and price.is_available
            and price.price_cents_per_litre is not None
        ),
        None,
    )
    if regular:
        return regular

    return next(
        (
            price
            for price in station.prices
            if price.is_available and price.price_cents_per_litre is not None
        ),
        None,
    )


def build_entry_title(user_input: dict[str, str], station: StationRecord) -> str:
    if user_input.get("entity_name"):
        return user_input["entity_name"]
    if station.brand and station.brand.lower() not in station.name.lower():
        return f"{station.brand} - {station.name}"
    return station.name
