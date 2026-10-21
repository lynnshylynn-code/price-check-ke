"""Prototype order records and a sandbox-only Daraja STK Push provider."""

from __future__ import annotations

import base64
import hmac
import json
import os
import re
import sqlite3
import uuid
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from .listings import get_listing

STATUSES = {"created", "payment_pending", "paid_sandbox", "failed", "cancelled"}
ALLOWED_TRANSITIONS = {
    "created": {"payment_pending", "paid_sandbox", "cancelled", "failed"},
    "payment_pending": {"paid_sandbox", "failed", "cancelled"},
    "failed": {"payment_pending", "cancelled"},
    "paid_sandbox": set(),
    "cancelled": set(),
}
SANDBOX_BASE_URL = "https://sandbox.safaricom.co.ke"


class PaymentProvider(Protocol):
    def pay(self, order_id: str) -> tuple[str, str | None]: ...


class HttpResponse(Protocol):
    def json(self) -> dict: ...
    def raise_for_status(self) -> None: ...


class HttpClient(Protocol):
    def get(self, url: str, *, headers: dict[str, str]) -> HttpResponse: ...
    def post(
        self, url: str, *, headers: dict[str, str], json: dict
    ) -> HttpResponse: ...


class UrllibResponse:
    def __init__(self, body: bytes, status: int):
        self.body = body
        self.status = status

    def json(self) -> dict:
        return json.loads(self.body)

    def raise_for_status(self) -> None:
        if self.status >= 400:
            raise RuntimeError(f"Daraja request failed with HTTP {self.status}")


class UrllibHttpClient:
    """Small stdlib transport; errors do not include request credentials or bodies."""

    @staticmethod
    def _request(request: Request) -> UrllibResponse:
        try:
            with urlopen(request, timeout=15) as response:
                return UrllibResponse(response.read(), response.status)
        except (HTTPError, URLError, TimeoutError) as error:
            raise RuntimeError("Daraja sandbox request failed") from error

    def get(self, url: str, *, headers: dict[str, str]) -> UrllibResponse:
        return self._request(Request(url, headers=headers, method="GET"))

    def post(self, url: str, *, headers: dict[str, str], json: dict) -> UrllibResponse:
        request = Request(
            url,
            data=__import__("json").dumps(json).encode(),
            headers={**headers, "Content-Type": "application/json"},
            method="POST",
        )
        return self._request(request)


class MockPaymentProvider:
    def __init__(self, succeeds: bool = True):
        self.succeeds = succeeds

    def pay(self, order_id: str) -> tuple[str, str | None]:
        if self.succeeds:
            return "paid_sandbox", f"MOCK-{order_id[:8]}"
        return "failed", None


def _db_path() -> Path:
    path = Path(os.getenv("PRICE_CHECK_ORDERS_DB", "backend/data/runtime/orders.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(_db_path())
    connection.row_factory = sqlite3.Row
    connection.execute("""CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY, store TEXT NOT NULL, lines TEXT NOT NULL,
        subtotal REAL NOT NULL, delivery_address TEXT NOT NULL,
        latitude REAL, longitude REAL, phone TEXT NOT NULL, status TEXT NOT NULL,
        created_at TEXT NOT NULL, payment_reference TEXT,
        merchant_request_id TEXT, checkout_request_id TEXT)""")
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(orders)")}
    for name in ("merchant_request_id", "checkout_request_id"):
        if name not in columns:
            connection.execute(f"ALTER TABLE orders ADD COLUMN {name} TEXT")
    connection.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_checkout_request "
        "ON orders(checkout_request_id) WHERE checkout_request_id IS NOT NULL"
    )
    return connection


def normalize_phone(value: str) -> str:
    digits = re.sub(r"[\s()+-]", "", value)
    if digits.startswith("0"):
        digits = "254" + digits[1:]
    elif digits.startswith("7") or digits.startswith("1"):
        digits = "254" + digits
    if not re.fullmatch(r"254[17]\d{8}", digits):
        raise ValueError("Enter a valid Kenyan phone number.")
    return digits


def create_order(payload: dict) -> dict:
    store = payload["store"].strip()
    address = payload["delivery_address"].strip()
    if not 10 <= len(address) <= 200:
        raise ValueError("Address must be 10 to 200 characters.")
    phone = normalize_phone(payload["phone"])
    lat, lon = payload.get("latitude"), payload.get("longitude")
    if (lat is None) != (lon is None):
        raise ValueError("Latitude and longitude must be provided together.")
    if lat is not None and not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("Coordinates are out of range.")
    requested = payload["items"]
    if not 1 <= len(requested) <= 30:
        raise ValueError("Order must contain 1 to 30 lines.")
    lines = []
    subtotal = Decimal("0")
    seen_ids = set()
    for row in requested:
        qty = row["quantity"]
        if not 1 <= qty <= 20:
            raise ValueError("Quantities must be between 1 and 20.")
        listing_id = row["listing_id"]
        if listing_id in seen_ids:
            raise ValueError("Each listing may appear only once; combine its quantity.")
        seen_ids.add(listing_id)
        item = get_listing(listing_id)
        if item is None or item.supermarket.casefold() != store.casefold():
            raise ValueError("Every listing must belong to the selected store.")
        unit_price = Decimal(str(item.price_kes))
        lines.append({
            "listing_id": item.id,
            "name": item.item_name,
            "price_kes": float(unit_price),
            "quantity": qty,
        })
        subtotal += unit_price * qty
    order_id = str(uuid.uuid4())
    created_at = datetime.now(UTC).isoformat()
    with _connect() as db:
        db.execute(
            """INSERT INTO orders (
            id,store,lines,subtotal,delivery_address,latitude,longitude,phone,status,
            created_at,payment_reference,merchant_request_id,checkout_request_id
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (order_id, store, json.dumps(lines), float(subtotal), address, lat, lon,
             phone, "created", created_at, None, None, None),
        )
    return get_order(order_id)  # type: ignore[return-value]


def _public(row: sqlite3.Row) -> dict:
    data = dict(row)
    data["lines"] = json.loads(data.pop("lines"))
    phone = data.pop("phone")
    data["phone"] = phone[:4] + "******" + phone[-2:]
    data["delivery_fee"] = None
    data["delivery_fee_note"] = "set by the supermarket at its own checkout"
    data["prototype_disclaimer"] = (
        "Prototype: this order is not sent to the supermarket and no real money moves."
    )
    return data


def get_order(order_id: str) -> dict | None:
    with _connect() as db:
        row = db.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    return _public(row) if row else None


def _get_internal_order(order_id: str) -> sqlite3.Row | None:
    with _connect() as db:
        return db.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()


def update_order(
    order_id: str,
    status: str,
    reference: str | None = None,
    merchant_request_id: str | None = None,
    checkout_request_id: str | None = None,
) -> dict | None:
    if status not in STATUSES:
        raise ValueError("Invalid order status.")
    with _connect() as db:
        current = db.execute("SELECT status FROM orders WHERE id=?", (order_id,)).fetchone()
        if current is None:
            return None
        if status not in ALLOWED_TRANSITIONS[current["status"]]:
            raise ValueError(f"Order cannot transition from {current['status']} to {status}.")
        db.execute(
            """UPDATE orders SET status=?,
               payment_reference=COALESCE(?,payment_reference),
               merchant_request_id=COALESCE(?,merchant_request_id),
               checkout_request_id=COALESCE(?,checkout_request_id) WHERE id=?""",
            (status, reference, merchant_request_id, checkout_request_id, order_id),
        )
    return get_order(order_id)


def save_payment_request(order_id: str, merchant_id: str, checkout_id: str) -> dict | None:
    return update_order(
        order_id,
        "payment_pending",
        merchant_request_id=merchant_id,
        checkout_request_id=checkout_id,
    )


def apply_mpesa_callback(
    checkout_id: str, result_code: int, amount: object | None, receipt: str | None
) -> tuple[str, dict | None]:
    with _connect() as db:
        row = db.execute(
            "SELECT * FROM orders WHERE checkout_request_id=?", (checkout_id,)
        ).fetchone()
        if row is None:
            raise LookupError("No order matches this checkout request.")
        desired = "paid_sandbox" if result_code == 0 else "failed"
        if row["status"] == desired:
            return "duplicate", _public(row)
        if row["status"] != "payment_pending":
            raise ValueError(f"Callback not allowed while order is {row['status']}.")
        reference = receipt if result_code == 0 else None
        if result_code == 0:
            try:
                amount_matches = (
                    amount is not None
                    and Decimal(str(amount)) == Decimal(str(row["subtotal"]))
                )
            except InvalidOperation:
                amount_matches = False
            if not amount_matches:
                raise ValueError("Callback amount does not match the order subtotal.")
        db.execute(
            "UPDATE orders SET status=?,payment_reference=COALESCE(?,payment_reference) "
            "WHERE id=?",
            (desired, reference, row["id"]),
        )
        updated = db.execute("SELECT * FROM orders WHERE id=?", (row["id"],)).fetchone()
    return "updated", _public(updated)


def delete_order(order_id: str) -> bool:
    with _connect() as db:
        cursor = db.execute("DELETE FROM orders WHERE id=?", (order_id,))
    return cursor.rowcount > 0


def build_stk_push_request(
    order: sqlite3.Row | dict, *, timestamp: datetime | None = None
) -> dict:
    shortcode = os.environ["DARAJA_SHORTCODE"]
    passkey = os.environ["DARAJA_PASSKEY"]
    party_b = os.getenv("DARAJA_PARTY_B", shortcode)
    transaction_type = os.getenv("DARAJA_TRANSACTION_TYPE", "CustomerPayBillOnline")
    if transaction_type not in {"CustomerPayBillOnline", "CustomerBuyGoodsOnline"}:
        raise ValueError("DARAJA_TRANSACTION_TYPE must be a supported STK transaction type.")
    callback_url = os.environ["DARAJA_CALLBACK_URL"]
    if not callback_url.startswith("https://"):
        raise ValueError("DARAJA_CALLBACK_URL must be a public HTTPS URL.")
    order_id = order["id"]
    subtotal = Decimal(str(order["subtotal"]))
    if subtotal < 1 or subtotal != subtotal.to_integral_value():
        raise ValueError("Daraja STK Push requires a whole-KES amount of at least KES 1.")
    phone = normalize_phone(order["phone"])
    timestamp = timestamp or datetime.now(ZoneInfo("Africa/Nairobi"))
    stamp = timestamp.strftime("%Y%m%d%H%M%S")
    password = base64.b64encode(f"{shortcode}{passkey}{stamp}".encode()).decode()
    return {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": stamp,
        "TransactionType": transaction_type,
        "Amount": int(subtotal),
        "PartyA": phone,
        "PartyB": party_b,
        "PhoneNumber": phone,
        "CallBackURL": callback_url,
        "AccountReference": order_id.replace("-", "")[:12],
        "TransactionDesc": "PriceCheck",
    }


class DarajaSandboxProvider:
    """M-Pesa Express request implementation, restricted to Safaricom sandbox."""

    def __init__(self, http_client: HttpClient | None = None):
        if os.getenv("PRICE_CHECK_PAYMENTS") != "daraja_sandbox":
            raise RuntimeError("Daraja sandbox payments are not enabled")
        base_url = os.getenv("DARAJA_BASE_URL", SANDBOX_BASE_URL).rstrip("/")
        if base_url != SANDBOX_BASE_URL:
            raise RuntimeError("Only the Safaricom Daraja sandbox URL is allowed")
        self.base_url = base_url
        self.consumer_key = os.getenv("DARAJA_CONSUMER_KEY", "")
        self.consumer_secret = os.getenv("DARAJA_CONSUMER_SECRET", "")
        if not self.consumer_key or not self.consumer_secret:
            raise RuntimeError("Daraja sandbox credentials are required")
        for name in (
            "DARAJA_SHORTCODE",
            "DARAJA_PASSKEY",
            "DARAJA_CALLBACK_URL",
            "PRICE_CHECK_CALLBACK_SECRET",
        ):
            if not os.getenv(name):
                raise RuntimeError(f"{name} is required for Daraja sandbox payments")
        callback_secret = os.environ["PRICE_CHECK_CALLBACK_SECRET"]
        callback_path = urlsplit(os.environ["DARAJA_CALLBACK_URL"]).path.rstrip("/")
        if not callback_path.endswith(f"/callback/{callback_secret}"):
            raise RuntimeError(
                "DARAJA_CALLBACK_URL must include the configured callback token path"
            )
        self.http = http_client or UrllibHttpClient()

    def _access_token(self) -> str:
        encoded = base64.b64encode(
            f"{self.consumer_key}:{self.consumer_secret}".encode()
        ).decode()
        url = f"{self.base_url}/oauth/v1/generate?{urlencode({'grant_type': 'client_credentials'})}"
        response = self.http.get(url, headers={"Authorization": f"Basic {encoded}"})
        response.raise_for_status()
        token = response.json().get("access_token")
        if not token:
            raise RuntimeError("Daraja authorization response did not contain an access token")
        return str(token)

    def pay(self, order_id: str) -> tuple[str, str | None]:
        order = _get_internal_order(order_id)
        if order is None:
            raise LookupError("Order not found.")
        if order["status"] not in {"created", "failed"}:
            raise ValueError(f"Order cannot be paid while it is {order['status']}.")
        token = self._access_token()
        payload = build_stk_push_request(order)
        response = self.http.post(
            f"{self.base_url}/mpesa/stkpush/v1/processrequest",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        response.raise_for_status()
        result = response.json()
        if str(result.get("ResponseCode")) != "0":
            raise RuntimeError("Daraja sandbox did not accept the STK Push request")
        merchant_id = result.get("MerchantRequestID")
        checkout_id = result.get("CheckoutRequestID")
        if not merchant_id or not checkout_id:
            raise RuntimeError("Daraja response is missing request identifiers")
        save_payment_request(order_id, str(merchant_id), str(checkout_id))
        return "payment_pending", str(checkout_id)


def callback_secret_matches(path_secret: str, expected: str | None) -> bool:
    return bool(expected) and hmac.compare_digest(path_secret, expected)
