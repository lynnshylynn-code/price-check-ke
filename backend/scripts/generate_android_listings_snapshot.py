"""Generate the Android offline listing snapshot from the canonical backend loader."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend/src"))

from price_check_api.listings import DATA_CAVEATS, DATA_LABEL, get_listings, listing_dict  # noqa: E402

destination = ROOT / "android-native/app/src/main/assets/listings_snapshot.json"
destination.parent.mkdir(parents=True, exist_ok=True)
payload = {
    "snapshot_label": "snapshot 20 Oct 2026",
    "data_label": DATA_LABEL,
    "caveats": DATA_CAVEATS,
    "items": [listing_dict(item) for item in get_listings()],
}
destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
print("android-native/app/src/main/assets/listings_snapshot.json")
print(f"Listings written: {len(payload['items'])}")
