import os
import threading
import time
from collections import deque

from fastapi import HTTPException, Request

_requests_by_ip: dict[str, deque[float]] = {}
_MAX_TRACKED_IPS = 10_000
_lock = threading.Lock()


def enforce_ai_rate_limit(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    # Forwarded headers are client-controlled unless the deployment explicitly
    # confirms that a trusted reverse proxy overwrites them.
    if os.getenv("PRICE_CHECK_TRUST_PROXY") == "1":
        forwarded_for = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
        if forwarded_for:
            client_ip = forwarded_for
    now = time.monotonic()
    window_seconds = int(os.getenv("PRICE_CHECK_AI_RATE_WINDOW_SECONDS", "60"))
    request_limit = int(os.getenv("PRICE_CHECK_AI_RATE_LIMIT", "60"))
    if window_seconds <= 0 or request_limit < 0:
        raise RuntimeError(
            "AI rate-limit window must be positive and request limit cannot be negative."
        )
    if request_limit == 0:
        return

    with _lock:
        for ip, timestamps in list(_requests_by_ip.items()):
            while timestamps and timestamps[0] <= now - window_seconds:
                timestamps.popleft()
            if not timestamps:
                del _requests_by_ip[ip]

        if client_ip not in _requests_by_ip and len(_requests_by_ip) >= _MAX_TRACKED_IPS:
            oldest_ip = min(_requests_by_ip, key=lambda ip: _requests_by_ip[ip][0])
            del _requests_by_ip[oldest_ip]

        timestamps = _requests_by_ip.setdefault(client_ip, deque())
        if len(timestamps) >= request_limit:
            retry_after = max(1, int(window_seconds - (now - timestamps[0])))
            raise HTTPException(
                status_code=429,
                detail=(
                    "AI request limit reached for this IP. "
                    "Please retry after the indicated delay."
                ),
                headers={"Retry-After": str(retry_after)},
            )
        timestamps.append(now)
