import csv
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_coverage import audit_coverage, county_from_context  # noqa: E402


def test_coverage_audit_counts_store_and_named_county(tmp_path: Path) -> None:
    source = tmp_path / "listings.csv"
    with source.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=["supermarket", "location_context"])
        writer.writeheader()
        writer.writerows(
            [
                {"supermarket": "Quickmart", "location_context": "Kilimani, Nairobi"},
                {"supermarket": "Naivas", "location_context": "delivery location unknown"},
            ]
        )

    report = audit_coverage(source)

    assert report["total_listing_rows"] == 2
    assert report["by_store"] == {"Naivas": 1, "Quickmart": 1}
    assert report["by_county"] == {"Nairobi": 1, "unknown/unverified": 1}


def test_county_extraction_does_not_infer_unmentioned_counties() -> None:
    assert county_from_context("Westlands selected") == "unknown/unverified"
