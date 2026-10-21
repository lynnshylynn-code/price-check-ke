import pytest
from fastapi.testclient import TestClient

from price_check_api import listings as listing_module
from price_check_api.listings import _stable_id, get_listings, parse_pack_size
from price_check_api.main import app

client = TestClient(app)


def test_real_snapshot_loads_and_keeps_disclosure() -> None:
    rows = get_listings()
    assert len(rows) == 239
    assert sum(row.supermarket == "Naivas" for row in rows) == 176
    assert sum(row.supermarket == "Carrefour" for row in rows) == 25
    assert sum(row.supermarket == "Quickmart" for row in rows) == 38
    response = client.get("/api/v1/listings", params={"store": "Naivas", "limit": 2})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 176
    assert "snapshot 2026-10-20" in payload["data_label"]
    assert "No dataset licence" in payload["caveats"]


def test_listing_filters_and_detail_endpoint() -> None:
    response = client.get("/api/v1/listings", params={
        "q": "milk", "grocery_only": "true", "max_price": 300, "limit": 100,
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] > 0
    assert all("milk" in row["item_name"].casefold() for row in payload["items"])
    item = payload["items"][0]
    detail = client.get(f"/api/v1/listings/{item['id']}")
    assert detail.status_code == 200
    assert detail.json()["item"]["product_url"] == item["product_url"]
    assert client.get("/api/v1/listings/not-a-listing").status_code == 404


def test_pack_size_parser_handles_real_formats() -> None:
    values = [
        "2kg", "200ml", "1l", "500ml", "250ml", "2L", "2 liters", "70 gr",
        "15 Pieces of Eggs", "30 Pieces", "1kg", "8g x 6", "1.5g", "4g x 40",
        "400g", "2Kg", "15PIECESOFEGGS", "6PC", "2LITERS",
    ]
    parsed = [parse_pack_size(value, {}) for value in values]
    assert len(parsed) >= 15
    assert all(value is not None for value in parsed)
    assert parsed[0] == (2.0, "kg")
    assert parsed[1] == (0.2, "l")
    assert parsed[11] == (0.048, "kg")
    assert parsed[16] == (15.0, "pcs")
    assert parse_pack_size(None, {}) is None
    assert parse_pack_size("assorted", {}) is None


def test_listing_identifier_is_stable_and_canonicalizes_tracking() -> None:
    first = _stable_id("Naivas", "HTTPS://Example.COM/item/123/?utm_source=feed")
    second = _stable_id("naivas", "https://example.com/item/123")
    assert first == second


def test_uom_table_is_optional_and_regex_fallback_still_works(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PRICE_CHECK_APHRC_XLSX", str(tmp_path / "missing.xlsx"))
    listing_module._load_uom.cache_clear()
    assert listing_module.get_uom_map() == {}
    assert parse_pack_size("2LITERS") == (2.0, "l")
    listing_module._load_uom.cache_clear()


def test_invalid_snapshot_record_fails_validation(tmp_path, monkeypatch) -> None:
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text(
        "supermarket,item_name,price_kes,product_url\nNaivas,Milk,0,https://example.com/milk\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PRICE_CHECK_LISTINGS_CSV", str(csv_path))
    listing_module._load_listings.cache_clear()
    with pytest.raises(listing_module.ListingDataError, match="positive"):
        listing_module.get_listings()
    listing_module._load_listings.cache_clear()
