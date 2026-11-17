"""Audit observed listing rows by retailer and any county named in location context."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LISTINGS = ROOT / "data/listings/kenya_supermarket_public_listings.csv"
COUNTIES = (
    "Mombasa", "Kwale", "Kilifi", "Tana River", "Lamu", "Taita Taveta", "Garissa",
    "Wajir", "Mandera", "Marsabit", "Isiolo", "Meru", "Tharaka Nithi", "Embu",
    "Kitui", "Machakos", "Makueni", "Nyandarua", "Nyeri", "Kirinyaga", "Murang'a",
    "Kiambu", "Turkana", "West Pokot", "Samburu", "Trans Nzoia", "Uasin Gishu",
    "Elgeyo Marakwet", "Nandi", "Baringo", "Laikipia", "Nakuru", "Narok", "Kajiado",
    "Kericho", "Bomet", "Kakamega", "Vihiga", "Bungoma", "Busia", "Siaya",
    "Kisumu", "Homa Bay", "Migori", "Kisii", "Nyamira", "Nairobi",
)
COUNTY_PATTERN = re.compile(
    r"\b("
    + "|".join(re.escape(county) for county in sorted(COUNTIES, key=len, reverse=True))
    + r")\b",
    re.IGNORECASE,
)


def county_from_context(context: str) -> str:
    """Extract an explicitly named Kenyan county or preserve unknown geography."""
    match = COUNTY_PATTERN.search(context)
    if not match:
        return "unknown/unverified"
    return next(county for county in COUNTIES if county.casefold() == match.group().casefold())


def audit_coverage(path: Path = DEFAULT_LISTINGS) -> dict[str, Any]:
    """Count listing rows by store and county without inferring branch coverage."""
    by_store: Counter[str] = Counter()
    by_county: Counter[str] = Counter()
    by_store_county: Counter[tuple[str, str]] = Counter()
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not {"supermarket", "location_context"}.issubset(reader.fieldnames or []):
            raise ValueError("listing file must include supermarket and location_context columns")
        for row in reader:
            store = row["supermarket"].strip() or "unknown"
            county = county_from_context(row["location_context"] or "")
            by_store[store] += 1
            by_county[county] += 1
            by_store_county[(store, county)] += 1
    return {
        "total_listing_rows": sum(by_store.values()),
        "by_store": dict(sorted(by_store.items())),
        "by_county": dict(sorted(by_county.items())),
        "by_store_and_county": {
            f"{store} | {county}": count
            for (store, county), count in sorted(by_store_county.items())
        },
        "interpretation": (
            "Counts are listing rows in the selected public snapshot. An unverified county "
            "or a retailer with zero rows is a data-coverage gap, not evidence of no stock."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--listings", type=Path, default=DEFAULT_LISTINGS)
    args = parser.parse_args()
    print(json.dumps(audit_coverage(args.listings), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
