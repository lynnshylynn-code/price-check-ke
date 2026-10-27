"""Write an unapproved CSV of Open Food Facts image candidates (no image downloads)."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from price_check_api.listings import get_listings

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/images/candidates.csv"
SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"
STAPLES = (
    ("maize flour", re.compile(r"\b(?:maize meal|maize flour|unga)\b", re.I)),
    ("beans", re.compile(r"\bbeans?\b", re.I)),
    ("rice", re.compile(r"\brice\b", re.I)),
    ("cooking oil", re.compile(r"\bcooking oil\b", re.I)),
    ("sugar", re.compile(r"\bsugar\b", re.I)),
    ("milk", re.compile(r"\bmilk\b", re.I)),
    ("bread", re.compile(r"\bbread\b", re.I)),
    ("wheat flour", re.compile(r"\b(?:wheat flour|all purpose flour|plain flour)\b", re.I)),
    ("tea", re.compile(r"\btea\b", re.I)),
    ("salt", re.compile(r"\bsalt\b", re.I)),
    ("green grams", re.compile(r"\bgreen grams?\b", re.I)),
    ("lentils", re.compile(r"\blentils?\b", re.I)),
    ("porridge flour", re.compile(r"\bporridge flour\b", re.I)),
    ("spaghetti", re.compile(r"\bspaghetti\b", re.I)),
    ("peanut butter", re.compile(r"\bpeanut butter\b", re.I)),
)
FIELDS = (
    "listing_id",
    "listing_product",
    "off_product_name",
    "image_url",
    "attribution",
    "source_page",
    "licence_note",
    "approved",
)
LICENCE_NOTE = (
    "Open Food Facts states product images are CC BY-SA; verify image-specific rights "
    "and attribution before approval."
)


def _image_attribution(product: dict[str, object]) -> str:
    images = product.get("images")
    if not isinstance(images, dict):
        return ""
    selected = images.get("front_en") or next(
        (value for key, value in images.items() if str(key).startswith("front_")), None
    )
    if not isinstance(selected, dict):
        return ""
    image_id = selected.get("imgid")
    uploaded = images.get(str(image_id)) if image_id is not None else None
    if isinstance(uploaded, dict) and isinstance(uploaded.get("uploader"), str):
        return f"Open Food Facts contributor: {uploaded['uploader']}"
    return ""


def _is_open_food_facts_image(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlsplit(value)
    host = parsed.hostname or ""
    return parsed.scheme == "https" and (
        host == "openfoodfacts.org" or host.endswith(".openfoodfacts.org")
    )


def search_product(term: str, user_agent: str) -> dict[str, object] | None:
    query = urlencode(
        {
            "search_terms": term,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": 5,
            "fields": "code,product_name,image_front_url,images",
        }
    )
    request = Request(
        f"{SEARCH_URL}?{query}",
        headers={"User-Agent": user_agent, "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        print(f"Search failed for {term!r}: {error}")
        return None
    products = payload.get("products", []) if isinstance(payload, dict) else []
    return next(
        (
            product
            for product in products
            if isinstance(product, dict)
            and _is_open_food_facts_image(product.get("image_front_url"))
        ),
        None,
    )


def suggest(limit: int = 15, contact_email: str | None = None) -> list[dict[str, str]]:
    if not 1 <= limit <= 15:
        raise ValueError("limit must be between 1 and 15")
    email = (contact_email or os.getenv("PRICE_CHECK_OFF_CONTACT_EMAIL", "")).strip()
    if not email:
        raise ValueError(
            "Set PRICE_CHECK_OFF_CONTACT_EMAIL to the maintainer contact "
            "before querying Open Food Facts."
        )
    user_agent = f"PriceCheckKE/1.0 ({email})"
    snapshot = get_listings()
    selected = []
    used_ids = set()
    for category, pattern in STAPLES:
        listing = next(
            (
                item
                for item in snapshot
                if item.id not in used_ids and item.grocery and pattern.search(item.item_name)
            ),
            None,
        )
        if listing:
            selected.append((category, listing))
            used_ids.add(listing.id)
    rows = []
    for index, (_category, listing) in enumerate(selected[:limit]):
        if index:
            time.sleep(6.2)  # Stay below Open Food Facts' 10 search requests/minute limit.
        product = search_product(listing.item_name, user_agent)
        if product is None:
            continue
        code = str(product.get("code", "")).strip()
        if not code:
            continue
        rows.append(
            {
                "listing_id": listing.id,
                "listing_product": listing.item_name,
                "off_product_name": str(product.get("product_name", "")),
                "image_url": str(product["image_front_url"]),
                "attribution": _image_attribution(product),
                "source_page": f"https://world.openfoodfacts.org/product/{code}",
                "licence_note": LICENCE_NOTE,
                "approved": "",
            }
        )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} unapproved suggestions to {OUTPUT}; no image files were downloaded.")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=15, help="1 to 15 staple product searches")
    arguments = parser.parse_args()
    suggest(arguments.limit)


if __name__ == "__main__":
    main()
