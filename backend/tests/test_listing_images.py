import json
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

import pytest

from price_check_api.listing_images import image_for_listing
from price_check_api.listings import get_listings, listing_dict

_SUGGEST_SCRIPT = Path(__file__).parents[1] / "scripts/suggest_images_off.py"
_SUGGEST_SPEC = spec_from_file_location("suggest_images_off", _SUGGEST_SCRIPT)
assert _SUGGEST_SPEC and _SUGGEST_SPEC.loader
suggest_images_off = module_from_spec(_SUGGEST_SPEC)
_SUGGEST_SPEC.loader.exec_module(suggest_images_off)


def test_only_complete_human_approved_images_are_merged(tmp_path) -> None:
    image_file = tmp_path / "product_images.json"
    approved = {
        "approved-1": {
            "approved": True,
            "image_url": "https://images.openfoodfacts.org/front.jpg",
            "attribution": "Open Food Facts contributor: sample-user",
            "source_page": "https://world.openfoodfacts.org/product/123",
            "licence_note": "CC BY-SA; verified by reviewer.",
        },
        "pending-1": {
            "approved": False,
            "image_url": "https://images.openfoodfacts.org/pending.jpg",
            "attribution": "",
            "source_page": "https://world.openfoodfacts.org/product/456",
            "licence_note": "Needs review.",
        },
        "incomplete-1": {"approved": True, "image_url": "https://images.example.org/no-credit.jpg"},
        "retailer-site-1": {
            "approved": True,
            "image_url": "https://supermarket.example.org/image.jpg",
            "attribution": "Open Food Facts contributor: sample-user",
            "source_page": "https://world.openfoodfacts.org/product/123",
            "licence_note": "CC BY-SA; verified by reviewer.",
        },
    }
    image_file.write_text(json.dumps({"items": approved}), encoding="utf-8")

    assert image_for_listing("approved-1", image_file) == {
        "image_url": "https://images.openfoodfacts.org/front.jpg",
        "attribution": "Open Food Facts contributor: sample-user",
        "source_page": "https://world.openfoodfacts.org/product/123",
        "licence_note": "CC BY-SA; verified by reviewer.",
    }
    assert image_for_listing("pending-1", image_file) is None
    assert image_for_listing("incomplete-1", image_file) is None
    assert image_for_listing("retailer-site-1", image_file) is None


def test_missing_image_file_returns_no_image(tmp_path) -> None:
    assert image_for_listing("any-listing", tmp_path / "missing.json") is None


def test_snapshot_listing_has_nullable_image_when_no_entry_is_approved() -> None:
    assert listing_dict(get_listings()[0])["image"] is None


def test_candidate_script_never_approves_suggestions_or_invents_attribution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output = tmp_path / "candidates.csv"
    observed = {}
    monkeypatch.setattr(suggest_images_off, "OUTPUT", output)
    monkeypatch.setattr(suggest_images_off.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        suggest_images_off,
        "get_listings",
        lambda: [
            SimpleNamespace(id="listing-1", item_name="Soko Flour Maize Meal 2kg", grocery=True)
        ],
    )

    def fake_search(term: str, user_agent: str) -> dict[str, object]:
        observed["term"] = term
        observed["user_agent"] = user_agent
        return {
            "code": "1234567890123",
            "product_name": "Example Maize Flour",
            "image_front_url": "https://images.openfoodfacts.org/front.jpg",
            "images": {"front_en": {"imgid": "1"}, "1": {"uploader": "contributor"}},
        }

    monkeypatch.setattr(suggest_images_off, "search_product", fake_search)
    rows = suggest_images_off.suggest(limit=1, contact_email="maintainer@example.org")

    assert observed["term"] == "Soko Flour Maize Meal 2kg"
    assert observed["user_agent"] == "PriceCheckKE/1.0 (maintainer@example.org)"
    assert rows[0]["listing_id"] == "listing-1"
    assert rows[0]["listing_product"] == "Soko Flour Maize Meal 2kg"
    assert rows[0]["attribution"] == "Open Food Facts contributor: contributor"
    assert rows[0]["approved"] == ""
    assert "verify image-specific rights" in rows[0]["licence_note"]
    assert "approved" in output.read_text(encoding="utf-8").splitlines()[0]
