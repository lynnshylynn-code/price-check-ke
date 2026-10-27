"""Validated, cached access to the advertised supermarket listing snapshot."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

DATA_LABEL = "Advertised prices, snapshot 2026-10-20, may differ in store"
DATA_CAVEATS = (
    "Partial public catalogue snapshot, not a sales dataset or price history. "
    "Stock, checkout price and promotion eligibility are unverified. Prices vary by "
    "store, location, session and promotion. No dataset licence was obtained or asserted."
)


@dataclass(frozen=True)
class Listing:
    id: str
    supermarket: str
    item_name: str
    price_kes: float
    regular_price_kes: float | None
    pack_size: str | None
    quantity: float | None
    unit: str | None
    unit_price: float | None
    discount_pct: float | None
    category: str
    category_source: str
    grocery: bool
    product_url: str
    listing_url: str
    location_context: str | None
    collected_at: str
    collection_method: str
    pack_size_source: str | None
    data_notes: str | None


class ListingDataError(ValueError):
    """The supplied snapshot cannot be parsed safely."""


def _canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ListingDataError("product_url must be an absolute HTTP(S) URL")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), "", ""))


def _stable_id(store: str, product_url: str) -> str:
    value = f"{store.strip().casefold()}|{_canonical_url(product_url)}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def _unit_key(value: str) -> str:
    return re.sub(r"\s+", "", value).upper()


@lru_cache(maxsize=2)
def _load_uom(path_text: str) -> dict[str, tuple[float, str]]:
    path = Path(path_text)
    if not path.is_file():
        return {}
    try:
        import pandas as pd

        frame = pd.read_excel(path, sheet_name="uom")
    except (ImportError, ValueError, OSError):
        return {}
    result: dict[str, tuple[float, str]] = {}
    for row in frame.to_dict("records"):
        try:
            result[_unit_key(str(row["uom_criteria"]))] = (
                float(row["conversion"]),
                str(row["standard_uom_criteria"]).casefold(),
            )
        except (KeyError, TypeError, ValueError):
            continue
    return result


def get_uom_map() -> dict[str, tuple[float, str]]:
    workbook = (
        Path(__file__).resolve().parents[2]
        / "data/listings/private/APHRC_supermarket_item_catalogue_and_dictionary.xlsx"
    )
    path = Path(
        os.getenv(
            "PRICE_CHECK_APHRC_XLSX",
            str(workbook),
        )
    )
    return _load_uom(str(path))


_UNIT_ALIASES = {
    "kg": "kg",
    "kgs": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    "g": "g",
    "gr": "g",
    "gram": "g",
    "grams": "g",
    "l": "l",
    "lt": "l",
    "ltr": "l",
    "ltrs": "l",
    "liter": "l",
    "liters": "l",
    "litre": "l",
    "litres": "l",
    "ml": "ml",
    "milliliter": "ml",
    "milliliters": "ml",
    "millilitre": "ml",
    "millilitres": "ml",
    "pc": "pcs",
    "pcs": "pcs",
    "piece": "pcs",
    "pieces": "pcs",
    "ct": "pcs",
    "count": "pcs",
}


def parse_pack_size(
    value: str | None, uom_map: dict[str, tuple[float, str]] | None = None
) -> tuple[float, str] | None:
    """Convert a clear size string to total kg, L, or pieces; leave ambiguity unknown."""
    if not value or not value.strip():
        return None
    text = value.strip()
    mapped = (uom_map if uom_map is not None else get_uom_map()).get(_unit_key(text))
    if mapped:
        quantity, mapped_unit = mapped
        if mapped_unit.startswith("kg"):
            unit = "kg"
        elif mapped_unit.startswith("ltr"):
            unit = "l"
        elif mapped_unit.startswith("pc"):
            unit = "pcs"
        else:
            unit = None
        if quantity > 0 and unit:
            return quantity, unit

    normalized = re.sub(r"\s+", " ", text.casefold()).strip()
    # Multipacks like 70 g x 5 use the total content; the pack remains one listing.
    multipack = re.fullmatch(
        r"(\d+(?:\.\d+)?)\s*(kg|kgs|kilograms?|g|gr|grams?|l|ltr|liters?|litres?|ml|millilit(?:er|re)s?)\s*[x×]\s*(\d+)",
        normalized,
    )
    if multipack:
        amount = float(multipack.group(1)) * int(multipack.group(3))
        unit = _UNIT_ALIASES[multipack.group(2)]
    else:
        per_unit = re.fullmatch(r"(?:per\s*)?(kg|kgs|kilograms?|l|ltr|liters?|litres?)", normalized)
        pieces = re.fullmatch(
            r"(\d+(?:\.\d+)?)\s*(?:pieces?(?:\s+of\s+\w+)?|pcs?|ct|count)", normalized
        )
        compact_pieces = re.fullmatch(r"(\d+(?:\.\d+)?)(?:pieces?)(?:of[a-z]+)?", normalized)
        size = re.fullmatch(
            r"(\d+(?:\.\d+)?)\s*(kg|kgs|kilograms?|g|gr|grams?|l|ltr|liters?|litres?|ml|millilit(?:er|re)s?)",
            normalized,
        )
        if per_unit:
            amount, unit = 1.0, _UNIT_ALIASES[per_unit.group(1)]
        elif pieces:
            amount, unit = float(pieces.group(1)), "pcs"
        elif compact_pieces:
            amount, unit = float(compact_pieces.group(1)), "pcs"
        elif size:
            amount, unit = float(size.group(1)), _UNIT_ALIASES[size.group(2)]
        else:
            return None
    if unit in {"g", "ml"}:
        return amount / 1000, "kg" if unit == "g" else "l"
    return amount, unit


_NON_GROCERY_NAME = re.compile(
    r"\b(?:whisk(?:y|ey)|vodka|gin|rum|brandy|wine|luggage|suitcase|blender|appliance|television|tv)\b",
    re.IGNORECASE,
)


def _category(name: str, grocery: bool) -> str:
    if not grocery:
        return "non_grocery"
    name = name.casefold()
    groups = {
        "produce": r"tomato|onion|potato|avocado|banana|mango|fruit|vegetable|spinach|sukuma",
        "dairy": r"milk|yoghurt|yogurt|cheese|butter|margarine|egg",
        "bakery": r"bread|loaf|bun|cake|biscuit|cracker",
        "beverages": r"juice|soda|cola|water|tea|coffee|drink|energy drink",
        "household": r"detergent|soap|tissue|toilet paper|cleaner|bleach|dishwash",
        "personal_care": r"toothpaste|shampoo|lotion|deodorant|sanitary|toothbrush",
    }
    return next(
        (category for category, pattern in groups.items() if re.search(pattern, name)),
        "pantry",
    )


def _parse_row(row: dict[str, str], uom_map: dict[str, tuple[float, str]]) -> Listing:
    name = (row.get("item_name") or "").strip()
    store = (row.get("supermarket") or "").strip()
    product_url = (row.get("product_url") or "").strip()
    try:
        price = float(row.get("price_kes", ""))
    except (TypeError, ValueError) as error:
        raise ListingDataError("price_kes must be a positive number") from error
    if not name or not product_url:
        raise ListingDataError("item_name and product_url must not be empty")
    if not store or price <= 0:
        raise ListingDataError("supermarket must be non-empty and price_kes positive")
    canonical_url = _canonical_url(product_url)
    raw_regular = (row.get("regular_price_kes") or "").strip()
    try:
        regular = float(raw_regular) if raw_regular else None
    except ValueError as error:
        raise ListingDataError("regular_price_kes must be numeric when present") from error
    if regular is not None and regular <= 0:
        raise ListingDataError("regular_price_kes must be positive when present")
    pack = (row.get("pack_size") or "").strip() or None
    parsed = parse_pack_size(pack, uom_map)
    quantity, unit = parsed if parsed else (None, None)
    divisor = {"kg": 1, "l": 1, "pcs": 1}.get(unit or "")
    unit_price = price / (quantity * divisor) if quantity and divisor else None
    grocery = price < 5000 and not _NON_GROCERY_NAME.search(name)
    category = _category(name, grocery)
    discount = ((regular - price) / regular * 100) if regular else None
    return Listing(
        id=_stable_id(store, canonical_url),
        supermarket=store,
        item_name=name,
        price_kes=price,
        regular_price_kes=regular,
        pack_size=pack,
        quantity=quantity,
        unit=unit,
        unit_price=round(unit_price, 4) if unit_price is not None else None,
        discount_pct=round(discount, 4) if discount is not None else None,
        category=category,
        category_source="conservative name rules; not human-verified",
        grocery=grocery,
        product_url=canonical_url,
        listing_url=(row.get("listing_url") or "").strip(),
        location_context=(row.get("location_context") or "").strip() or None,
        collected_at=(row.get("collected_at") or "").strip(),
        collection_method=(row.get("collection_method") or "").strip(),
        pack_size_source=(row.get("pack_size_source") or "").strip() or None,
        data_notes=(row.get("data_notes") or "").strip() or None,
    )


@lru_cache(maxsize=2)
def _load_listings(csv_path: str, uom_path: str) -> tuple[Listing, ...]:
    uom = _load_uom(uom_path)
    listings: list[Listing] = []
    try:
        with Path(csv_path).open(encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            required = {"supermarket", "item_name", "price_kes", "product_url"}
            if not reader.fieldnames or not required.issubset(reader.fieldnames):
                raise ListingDataError("listing CSV is missing required columns")
            for line, row in enumerate(reader, start=2):
                try:
                    listings.append(_parse_row(row, uom))
                except ListingDataError as error:
                    message = f"invalid listing at CSV line {line}: {error}"
                    raise ListingDataError(message) from error
    except OSError as error:
        raise ListingDataError(f"listing snapshot unavailable: {error}") from error
    return tuple(listings)


def get_listings() -> tuple[Listing, ...]:
    root = Path(__file__).resolve().parents[2]
    csv_path = Path(
        os.getenv(
            "PRICE_CHECK_LISTINGS_CSV",
            str(root / "data/listings/kenya_supermarket_public_listings.csv"),
        )
    )
    xlsx_path = Path(
        os.getenv(
            "PRICE_CHECK_APHRC_XLSX",
            str(
                root / "data/listings/private/APHRC_supermarket_item_catalogue_and_dictionary.xlsx"
            ),
        )
    )
    return _load_listings(str(csv_path), str(xlsx_path))


def get_listing(listing_id: str) -> Listing | None:
    return next((item for item in get_listings() if item.id == listing_id), None)


def search_listings(
    query: str,
    store: str | None = None,
    grocery_only: bool = False,
    max_price: float | None = None,
    limit: int = 10,
) -> tuple[Listing, ...]:
    words = re.findall(r"[a-z0-9]+", query.casefold())
    results = []
    for item in get_listings():
        name = item.item_name.casefold()
        if words and not all(word in name for word in words):
            continue
        if store and item.supermarket.casefold() != store.casefold():
            continue
        if grocery_only and not item.grocery:
            continue
        if max_price is not None and item.price_kes > max_price:
            continue
        results.append(item)
    return tuple(sorted(results, key=lambda item: (item.price_kes, item.supermarket))[:limit])


@lru_cache(maxsize=1)
def _listing_predictions() -> dict[str, dict[str, object]]:
    path = Path(__file__).resolve().parents[2] / "data/listings/listing_predictions.json"
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def listing_dict(listing: Listing) -> dict[str, object]:
    result: dict[str, object] = asdict(listing)
    prediction = _listing_predictions().get(listing.id)
    if prediction:
        for label in ("food_group", "nova"):
            item = prediction.get(label)
            if isinstance(item, dict) and item.get("predicted") is True:
                result[label] = item.get("value")
                result[f"{label}_confidence"] = item.get("confidence")
                result[f"{label}_predicted"] = True
    return result
