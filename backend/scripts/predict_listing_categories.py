"""Optionally enrich the public snapshot using labelled catalogue vocabulary."""

from __future__ import annotations

import json
import os
from pathlib import Path

from price_check_api.listings import get_listings

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = Path(
    os.getenv(
        "PRICE_CHECK_APHRC_XLSX",
        str(ROOT / "data/listings/private/APHRC_supermarket_item_catalogue_and_dictionary.xlsx"),
    )
)
OUTPUT = ROOT / "data/listings/listing_predictions.json"


def main() -> None:
    if not WORKBOOK.is_file():
        print("APHRC workbook is absent; no predictions were written.")
        return
    import pandas as pd
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    catalogue = pd.read_excel(WORKBOOK, sheet_name="unique_items")
    required = {"description", "food_group", "nova"}
    if not required.issubset(catalogue.columns):
        raise ValueError(f"unique_items must contain columns {sorted(required)}")
    catalogue = catalogue.dropna(subset=["description", "food_group", "nova"])
    names = catalogue["description"].astype(str).tolist()
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5))
    matrix = vectorizer.fit_transform(names)
    predictions = {}
    for listing in get_listings():
        scores = cosine_similarity(vectorizer.transform([listing.item_name]), matrix)[0]
        index = int(scores.argmax())
        confidence = float(scores[index])
        row = catalogue.iloc[index]
        predictions[listing.id] = {
            "food_group": {
                "value": str(row["food_group"]),
                "confidence": confidence,
                "predicted": True,
            },
            "nova": {"value": str(row["nova"]), "confidence": confidence, "predicted": True},
        }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(predictions, indent=2), encoding="utf-8")
    print(f"Wrote optional predictions for {len(predictions)} snapshot listings.")


if __name__ == "__main__":
    main()
