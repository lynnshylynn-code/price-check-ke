"""Create the AI-written scripted dialogue evaluation set."""

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/assistant/dialogues_eval.json"

seeds = [
    ["Where is the cheapest milk?", "and at Naivas?", "show more", "why?"],
    ["What is the price of sugar at Naivas?", "what about Quickmart?", "and for eggs?"],
    ["beans price in Kitui", "and in Garissa?", "what about maize?", "and in 2023?"],
    ["cheapest maize flour", "only at Carrefour", "others?"],
    ["what is the latest food inflation?", "why?", "thanks"],
    ["what offers are at Naivas?", "only at Quickmart", "show more"],
    ["cheapest bread", "at Tuskys?", "why?"],
    ["price of maize in Nairobi", "and beans?", "in 2022?"],
    ["cheapest cooking oil", "what about rice?", "and at Carrefour?"],
    ["food inflation latest", "show more", "what is the cheapest milk?"],
    ["where is cheapest sugar?", "only at Quickmart", "thanks"],
    ["beans price in Mombasa", "what about maize?", "in 2024?"],
    ["best deal on yoghurt", "and at Naivas?", "explain"],
    ["find the price of eggs", "what about bread?", "show more"],
    ["latest maize price in Kisumu", "and in Nakuru?", "why?"],
    ["cheapest tea", "at Quickmart?", "others?"],
    ["food inflation average", "in 2020?", "thank you"],
    ["cheapest beans", "and for maize flour?", "at Naivas?"],
    ["what deals are on at Carrefour?", "only at Naivas", "why?"],
    ["price of maize in Kitui", "what about beans?", "and in Garissa?"],
    ["cheapest milk", "show more", "at Quickmart?"],
    ["does it rain tomorrow?", "cheapest sugar", "why?"],
    ["cheapest cooking oil", "at Tuskys?", "what about eggs?"],
    ["latest food inflation", "what about 2021?", "cheapest bread"],
    ["price of maize in Nairobi", "and in 2023?", "what about beans?"],
    ["What is the price at Quickmart?", "milk", "and at Naivas?"],
]

listings_path = ROOT / "data/listings/kenya_supermarket_public_listings.csv"
with listings_path.open(encoding="utf-8-sig", newline="") as source:
    listings = list(csv.DictReader(source))
stores = sorted({row["supermarket"] for row in listings}, key=len, reverse=True)
dialogues = []
for index, turns in enumerate(seeds, start=1):
    scripted_turns = []
    for message in turns:
        checks = [
            {"type": "response_shape"},
            {"type": "no_advice_or_forecast"},
            {"type": "listing_sources_in_snapshot"},
            {"type": "cited_listing_prices_match_snapshot"},
        ]
        store = next(
            (
                name for name in stores
                if re.search(rf"(?<!\w){re.escape(name)}(?!\w)", message, re.I)
            ),
            None,
        )
        if store:
            checks.append({"type": "named_store_mentioned", "store": store})
        elif re.search(r"\bTuskys\b", message, re.I):
            checks.append({"type": "unknown_store_declared", "store": "Tuskys"})
        scripted_turns.append({"user": message, "CHECKS": checks})
    dialogues.append({
        "dialogue_id": f"eval_{index:02}",
        "source": "ai_written",
        "turns": scripted_turns,
    })

OUTPUT.write_text(json.dumps({"source": "ai_written", "dialogues": dialogues}, indent=2),
                  encoding="utf-8")
print(f"Wrote {len(dialogues)} AI-written evaluation dialogues to {OUTPUT}")
