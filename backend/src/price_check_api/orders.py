"""Local prototype orders; records never reach a supermarket."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from .listings import get_listing

STATUSES = {"created", "payment_pending", "paid_sandbox", "failed", "cancelled"}


class PaymentProvider(Protocol):
    def pay(self, order_id: str) -> tuple[str, str | None]: ...


class MockPaymentProvider:
    def pay(self, order_id: str) -> tuple[str, str | None]:
        return "paid_sandbox", f"MOCK-{order_id[:8]}"


class DarajaSandboxProvider:
    """Explicit sandbox-only guard; credentials remain in environment variables."""

    base_url = "https://sandbox.safaricom.co.ke"

    def __init__(self) -> None:
        if os.getenv("PRICE_CHECK_PAYMENTS") != "daraja_sandbox":
            raise RuntimeError("Daraja sandbox payments are not enabled")
        if os.getenv("DARAJA_BASE_URL", self.base_url) != self.base_url:
            raise RuntimeError("Only the Safaricom Daraja sandbox URL is allowed")
        self.consumer_key = os.getenv("DARAJA_CONSUMER_KEY", "")
        self.consumer_secret = os.getenv("DARAJA_CONSUMER_SECRET", "")
        if not self.consumer_key or not self.consumer_secret:
            raise RuntimeError("Daraja sandbox credentials are required")

    def pay(self, order_id: str) -> tuple[str, str | None]:
        # Initiation requires merchant shortcode/passkey and an externally reachable
        # callback URL. Until configured, do not fabricate a successful payment.
        required = ("DARAJA_SHORTCODE", "DARAJA_PASSKEY", "DARAJA_CALLBACK_URL")
        if any(not os.getenv(name) for name in required):
            raise RuntimeError("Daraja sandbox shortcode, passkey and callback URL are required")
        return "payment_pending", None


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
        created_at TEXT NOT NULL, payment_reference TEXT)""")
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
    store = payload["store"]
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
    subtotal = 0.0
    for row in requested:
        qty = row["quantity"]
        if not 1 <= qty <= 20:
            raise ValueError("Quantities must be between 1 and 20.")
        item = get_listing(row["listing_id"])
        if item is None or item.supermarket != store:
            raise ValueError("Every listing must belong to the selected store.")
        line = {"listing_id": item.id, "name": item.item_name,
                "price_kes": item.price_kes, "quantity": qty}
        lines.append(line)
        subtotal += item.price_kes * qty
    order_id = str(uuid.uuid4())
    created_at = datetime.now(UTC).isoformat()
    with _connect() as db:
        db.execute("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (order_id, store, json.dumps(lines), subtotal, address, lat, lon,
                    phone, "created", created_at, None))
    return get_order(order_id)  # type: ignore[return-value]


def _public(row: sqlite3.Row) -> dict:
    data = dict(row)
    data["lines"] = json.loads(data.pop("lines"))
    data["phone"] = data["phone"][:4] + "******" + data["phone"][-2:]
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


def update_order(order_id: str, status: str, reference: str | None = None) -> dict | None:
    if status not in STATUSES:
        raise ValueError("Invalid order status.")
    with _connect() as db:
        db.execute(
            "UPDATE orders SET status=?, payment_reference=COALESCE(?, payment_reference) "
            "WHERE id=?",
            (status, reference, order_id),
        )
    return get_order(order_id)


def delete_order(order_id: str) -> bool:
    with _connect() as db:
        cursor = db.execute("DELETE FROM orders WHERE id=?", (order_id,))
    return cursor.rowcount > 0
