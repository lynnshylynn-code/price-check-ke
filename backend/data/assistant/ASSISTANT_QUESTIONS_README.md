# Assistant training questions (synthetic)

**Provenance.** These templates were written by an AI assistant, not by people who use the app.
Every question generated from them is **synthetic training data**. Say so in the report.
They must **never** be used as the test set. `heldout_test_questions.csv` is a separate
AI-written held-out set (91 rows with `source=ai_written`); it is not human-authored test data.
Do not train on it, tune on it, or copy its questions into templates. Any future rows marked
`source=human` must be evaluated and reported separately.

## Files
- `assistant_question_templates.csv` - 228 templates in 68 families.
  Columns: `template_id`, `family_id`, `intent`, `style`, `template`, `slots`.
  Styles: formal, short, casual, typo, swahili_mix.
- `assistant_slot_values.csv` - values for each `{slot}`: `slot`, `surface_form`, `canonical`, `note`.
  `canonical` is the entity the linker should resolve to. Some rows are deliberately NOT in the data
  (other stores, unknown products, counties with no prices) to test graceful "not in the snapshot" answers.

## Intents and labelling rules
| intent | meaning | answer comes from |
|---|---|---|
| cheapest_item | lowest-priced listing for a product, group or category (the store is part of the answer) | listings |
| price_at_store | price of a named product or group at a named store | listings |
| compare_stores | explicit comparison of named stores, one product across all stores, or a small basket | listing groups |
| biggest_discount | largest discounts, offers, promotions, crossed-out prices | listings (regular vs advertised) |
| unit_price | price per kg / litre / 100 g / piece, "best value per unit" | listings (unit_price) |
| market_price | county + commodity prices from the World Bank RTFP data | market data |
| food_inflation | national food inflation / food price index | RTFP series |
| out_of_scope | greetings, chit-chat, news, coding, advice, forecasts, stock/delivery, gibberish | refuse politely |

Ambiguity rules (keep the labels consistent):
1. Asks for per-kg / per-litre / per-unit / "best value per unit" -> `unit_price`, even if a store is named.
2. Names two stores, says "across all stores", or asks about a basket -> `compare_stores`.
3. Asks "who sells X cheapest" / "cheapest X" -> `cheapest_item`. Asks "how much is X at STORE" -> `price_at_store`.
4. **Forecasts** ("what will sugar cost next month") are `out_of_scope` because the data cannot support them.
5. **Stock and delivery** questions are `out_of_scope` (stock, checkout price and delivery are not verified in the data).
6. A store or product that is not in the data (Tuskys, "an iPhone 15") keeps the intent
   `price_at_store`; the entity linker must answer "not in the snapshot" instead of guessing.
7. A county with no price data (Kisumu, Nakuru; Nairobi/Mombasa for maize) keeps the intent `market_price`;
   the answer must say no observations exist.

## How to expand (sketch)
```python
import csv, random, re
random.seed(42)
slots = {}
for r in csv.DictReader(open("assistant_slot_values.csv", encoding="utf-8")):
    slots.setdefault(r["slot"], []).append(r)

def fill(tpl):
    chosen = {}
    for s in set(re.findall(r"\{(\w+)\}", tpl)):
        chosen[s] = random.choice(slots[s])
    # pairs must differ on the CANONICAL value, not the surface form
    for a, b in (("store", "store2"), ("county", "county2"), ("group", "group2")):
        if a in chosen and b in chosen:
            while chosen[a]["canonical"] == chosen[b]["canonical"]:
                chosen[b] = random.choice(slots[b])
    q = tpl
    for s, r in chosen.items():
        q = q.replace("{" + s + "}", r["surface_form"])
    return q, {s: r["canonical"] for s, r in chosen.items()}
```
Then: sample 15-20 fillings per template (cap per template so no template dominates),
add random character noise (dropped/swapped letters, lowercase) to about 20%
of questions, and store `question, intent, family_id, entities`.

## Splitting (important)
Split by **`family_id`**, never by row. Paraphrases inside a family are near-duplicates, so they must
land on the same side of the split. Keep each intent represented in train, validation, and test.
A random row split would leak and inflate accuracy. Save family lists and print per-split counts.

## Things to verify before using
- Product names and prices come from the 20 Oct 2026 snapshot; re-check names if the snapshot changes.
- County coverage notes (which county has maize, beans or goat data) come from the RTFP file in the repo; the generator should read the real coverage instead of trusting these notes.
- Goat prices are per unit, not per kg; confirm in the data dictionary before writing answer templates.
- Swahili and sheng-style phrases were written to be simple and natural; have a Swahili speaker skim them.
