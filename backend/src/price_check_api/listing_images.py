"""Load only human-approved, attributed product images for listing responses."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

IMAGE_DATA_PATH = Path(__file__).resolve().parents[2] / "data/images/product_images.json"
_REQUIRED_FIELDS = ("image_url", "attribution", "source_page", "licence_note")


def _is_open_food_facts_url(value: str) -> bool:
    parsed = urlsplit(value)
    host = parsed.hostname or ""
    return parsed.scheme == "https" and (
        host == "openfoodfacts.org" or host.endswith(".openfoodfacts.org")
    )


@lru_cache(maxsize=4)
def _approved_images(path: str) -> dict[str, dict[str, str]]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    items = payload.get("items", {}) if isinstance(payload, dict) else {}
    if not isinstance(items, dict):
        return {}
    result = {}
    for listing_id, item in items.items():
        if not isinstance(item, dict) or item.get("approved") is not True:
            continue
        values = {field: item.get(field) for field in _REQUIRED_FIELDS}
        if not all(isinstance(value, str) and value.strip() for value in values.values()):
            continue
        image_url = values["image_url"]
        source_page = values["source_page"]
        if _is_open_food_facts_url(image_url) and _is_open_food_facts_url(source_page):
            result[str(listing_id)] = {field: str(values[field]) for field in _REQUIRED_FIELDS}
    return result


def image_for_listing(listing_id: str, path: Path = IMAGE_DATA_PATH) -> dict[str, str] | None:
    """Return complete image metadata only after explicit human approval."""
    return _approved_images(str(path)).get(listing_id)
