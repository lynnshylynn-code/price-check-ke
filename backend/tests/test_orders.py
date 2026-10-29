from datetime import datetime
from decimal import Decimal

import pytest

from price_check_api import orders
from price_check_api.listings import get_listings


@pytest.fixture
def order_setup(tmp_path, monkeypatch):
    monkeypatch.setenv("PRICE_CHECK_ORDERS_DB", str(tmp_path / "orders.sqlite3"))
    listing = next(item for item in get_listings() if item.price_kes.is_integer())
    payload = {
        "store": listing.supermarket,
        "items": [{"listing_id": listing.id, "quantity": 2}],
        "delivery_address": "123 Example Road Nairobi",
        "phone": "0712345678",
        "latitude": None,
        "longitude": None,
    }
    return listing, payload, orders.create_order(payload)


def test_order_prices_are_recomputed_masks_phone_and_delete_erases_data(order_setup):
    listing, payload, order = order_setup
    payload["items"][0]["price_kes"] = 0
    assert order["phone"] == "2547******78"
    assert order["delivery_fee"] is None
    assert order["delivery_fee_note"] == "set by the supermarket at its own checkout"
    assert order["status"] == "created"
    assert order["subtotal"] == listing.price_kes * 2
    assert order["lines"][0]["price_kes"] == listing.price_kes
    assert orders.delete_order(order["id"])
    assert orders.get_order(order["id"]) is None


@pytest.mark.parametrize("phone", ["123", "+2547000000000", "071234567"])
def test_rejects_invalid_kenyan_phone(phone):
    with pytest.raises(ValueError, match="valid Kenyan phone"):
        orders.normalize_phone(phone)


@pytest.mark.parametrize("address", ["short", "x" * 201])
def test_rejects_invalid_address(order_setup, address):
    _, payload, _ = order_setup
    payload["delivery_address"] = address
    with pytest.raises(ValueError, match="Address must be"):
        orders.create_order(payload)


def test_rejects_store_mismatch_and_invalid_coordinates(order_setup):
    listing, payload, _ = order_setup
    other_store_item = next(
        item for item in get_listings() if item.supermarket != listing.supermarket
    )
    payload["items"] = [{"listing_id": other_store_item.id, "quantity": 1}]
    with pytest.raises(ValueError, match="belong to the selected store"):
        orders.create_order(payload)
    payload["items"] = [{"listing_id": listing.id, "quantity": 1}]
    payload.update(latitude=100, longitude=0)
    with pytest.raises(ValueError, match="Coordinates"):
        orders.create_order(payload)
    payload.update(latitude=1, longitude=None)
    with pytest.raises(ValueError, match="provided together"):
        orders.create_order(payload)


def test_rejects_out_of_range_quantity_and_duplicate_lines(order_setup):
    listing, payload, _ = order_setup
    payload["items"] = [{"listing_id": listing.id, "quantity": 21}]
    with pytest.raises(ValueError, match="Quantities"):
        orders.create_order(payload)
    payload["items"] = [
        {"listing_id": listing.id, "quantity": 1},
        {"listing_id": listing.id, "quantity": 1},
    ]
    with pytest.raises(ValueError, match="only once"):
        orders.create_order(payload)


def test_rejects_basket_over_line_cap(order_setup):
    listing, payload, _ = order_setup
    payload["items"] = [
        {"listing_id": f"unknown-{index}", "quantity": 1} for index in range(31)
    ]
    with pytest.raises(ValueError, match="1 to 30 lines"):
        orders.create_order(payload)


def test_status_transition_table_rejects_illegal_change(order_setup):
    _, _, order = order_setup
    pending = orders.update_order(order["id"], "payment_pending")
    assert pending["status"] == "payment_pending"
    with pytest.raises(ValueError, match="cannot transition"):
        orders.update_order(order["id"], "created")
    cancelled = orders.update_order(order["id"], "cancelled")
    assert cancelled["status"] == "cancelled"
    with pytest.raises(ValueError, match="cannot transition"):
        orders.update_order(order["id"], "paid_sandbox")


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def json(self):
        return self.data

    def raise_for_status(self):
        return None


class FakeDarajaHttp:
    def __init__(self):
        self.get_request = None
        self.post_request = None

    def get(self, url, *, headers):
        self.get_request = (url, headers)
        return FakeResponse({"access_token": "test-access-token"})

    def post(self, url, *, headers, json):
        self.post_request = (url, headers, json)
        return FakeResponse({
            "ResponseCode": "0",
            "MerchantRequestID": "merchant-123",
            "CheckoutRequestID": "checkout-456",
        })


def test_daraja_sandbox_builds_request_and_saves_correlation(order_setup, monkeypatch):
    _, _, order = order_setup
    for name, value in {
        "PRICE_CHECK_PAYMENTS": "daraja_sandbox",
        "DARAJA_BASE_URL": orders.SANDBOX_BASE_URL,
        "DARAJA_CONSUMER_KEY": "test-key",
        "DARAJA_CONSUMER_SECRET": "test-secret",
        "DARAJA_SHORTCODE": "174379",
        "DARAJA_PASSKEY": "sandbox-passkey",
        "DARAJA_CALLBACK_URL": "https://example.test/callback/secret-token",
        "PRICE_CHECK_CALLBACK_SECRET": "secret-token",
        "DARAJA_PARTY_B": "174379",
        "DARAJA_TRANSACTION_TYPE": "CustomerPayBillOnline",
    }.items():
        monkeypatch.setenv(name, value)
    fake = FakeDarajaHttp()
    provider = orders.DarajaSandboxProvider(fake)
    status, reference = provider.pay(order["id"])
    assert status == "payment_pending"
    assert reference == "checkout-456"
    assert fake.get_request[0] == (
        "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    )
    url, headers, body = fake.post_request
    assert url.endswith("/mpesa/stkpush/v1/processrequest")
    assert headers["Authorization"] == "Bearer test-access-token"
    assert body["BusinessShortCode"] == "174379"
    assert body["Amount"] == order["subtotal"]
    assert body["PartyA"] == body["PhoneNumber"] == "254712345678"
    assert body["AccountReference"] == order["id"].replace("-", "")[:12]
    updated = orders.get_order(order["id"])
    assert updated["status"] == "payment_pending"
    assert updated["merchant_request_id"] == "merchant-123"
    assert updated["checkout_request_id"] == "checkout-456"


def test_stk_password_timestamp_generation(order_setup, monkeypatch):
    _, _, order = order_setup
    monkeypatch.setenv("DARAJA_SHORTCODE", "174379")
    monkeypatch.setenv("DARAJA_PASSKEY", "pass")
    monkeypatch.setenv("DARAJA_CALLBACK_URL", "https://example.test/callback/token")
    monkeypatch.setenv("PRICE_CHECK_CALLBACK_SECRET", "token")
    internal = orders._get_internal_order(order["id"])
    body = orders.build_stk_push_request(
        internal, timestamp=datetime(2026, 10, 21, 14, 5, 6)
    )
    assert body["Timestamp"] == "20261021140506"
    import base64
    assert base64.b64decode(body["Password"]).decode() == "174379pass20261021140506"


def test_callback_amount_check_duplicate_and_failed_payment(order_setup):
    _, _, order = order_setup
    orders.update_order(
        order["id"], "payment_pending", checkout_request_id="checkout-test"
    )
    with pytest.raises(ValueError, match="amount does not match"):
        orders.apply_mpesa_callback("checkout-test", 0, Decimal("1"), "RCPT1")
    assert orders.get_order(order["id"])["status"] == "payment_pending"
    outcome, paid = orders.apply_mpesa_callback(
        "checkout-test", 0, order["subtotal"], "RCPT1"
    )
    assert outcome == "updated" and paid["status"] == "paid_sandbox"
    duplicate, _ = orders.apply_mpesa_callback(
        "checkout-test", 0, order["subtotal"], "RCPT1"
    )
    assert duplicate == "duplicate"
    with pytest.raises(LookupError, match="No order matches"):
        orders.apply_mpesa_callback("unknown-checkout", 0, 1, None)


def test_failed_callback_and_callback_secret(order_setup):
    _, _, order = order_setup
    orders.update_order(
        order["id"], "payment_pending", checkout_request_id="checkout-fail"
    )
    outcome, failed = orders.apply_mpesa_callback("checkout-fail", 1032, None, None)
    assert outcome == "updated" and failed["status"] == "failed"
    duplicate, _ = orders.apply_mpesa_callback("checkout-fail", 1032, None, None)
    assert duplicate == "duplicate"
    assert orders.callback_secret_matches("expected", "expected")
    assert not orders.callback_secret_matches("wrong", "expected")
    assert not orders.callback_secret_matches("expected", None)


def test_production_daraja_url_is_rejected(monkeypatch):
    monkeypatch.setenv("PRICE_CHECK_PAYMENTS", "daraja_sandbox")
    monkeypatch.setenv("DARAJA_BASE_URL", "https://api.safaricom.co.ke")
    monkeypatch.setenv("DARAJA_CONSUMER_KEY", "key")
    monkeypatch.setenv("DARAJA_CONSUMER_SECRET", "secret")
    with pytest.raises(RuntimeError, match="sandbox URL"):
        orders.DarajaSandboxProvider()
