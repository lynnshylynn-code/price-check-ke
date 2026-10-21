import pytest

from price_check_api import orders
from price_check_api.listings import get_listings


def test_order_creation_masks_phone_and_delete_erases_record(tmp_path, monkeypatch):
    monkeypatch.setenv("PRICE_CHECK_ORDERS_DB", str(tmp_path / "orders.sqlite3"))
    item = orders.get_listing("not-a-real-id")
    assert item is None
    listing = get_listings()[0]
    order = orders.create_order({
        "store": listing.supermarket,
        "items": [{"listing_id": listing.id, "quantity": 2}],
        "delivery_address": "123 Example Road Nairobi",
        "phone": "0712345678",
        "latitude": None,
        "longitude": None,
    })
    assert order["phone"] == "2547******78"
    assert order["delivery_fee"] is None
    assert order["status"] == "created"
    assert orders.update_order(order["id"], "paid_sandbox")["status"] == "paid_sandbox"
    assert orders.delete_order(order["id"])
    assert orders.get_order(order["id"]) is None


@pytest.mark.parametrize("phone", ["123", "+2547000000000", "071234567"])
def test_rejects_invalid_kenyan_phone(phone):
    with pytest.raises(ValueError, match="valid Kenyan phone"):
        orders.normalize_phone(phone)


def test_production_daraja_url_is_rejected(monkeypatch):
    monkeypatch.setenv("PRICE_CHECK_PAYMENTS", "daraja_sandbox")
    monkeypatch.setenv("DARAJA_BASE_URL", "https://api.safaricom.co.ke")
    with pytest.raises(RuntimeError, match="sandbox URL"):
        orders.DarajaSandboxProvider()
