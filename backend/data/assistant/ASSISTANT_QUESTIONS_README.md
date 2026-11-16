# Assistant training questions (synthetic)

**Provenance.** These templates were written by an AI assistant, not by people who use the app.
Every question generated from them is **synthetic training data**. Say so in the report.
They must **never** be used as the test set. `heldout_test_questions.csv` is a separate
AI-written held-out set (91 rows with `source=ai_written`); it is not human-authored test data.
Do not train on it, tune on it, or copy its questions into templates. Any future rows marked
`source=human` must be evaluated and reported separately.

## Human evaluation draft

`human_test_questions_draft.csv` contains AI-generated candidate questions, not human-written
evaluation data. It is intentionally separate from the training and evaluation scripts, and every
row is marked `pending`. A human reviewer must confirm or rewrite each question and independently
confirm its intent label. A fluent Swahili/Sheng speaker must review the translated or mixed-language
wording. Remove or correct any ambiguous examples.

The four `price_at_store` candidates include observed supermarket examples; their `review_notes`
record the product, advertised price, source, date, and available Nairobi location context:
Naivas Nairobi delivery, Quickmart Westlands 24 HRS, Jaza Nairobi delivery, and Carrefour Westlands
from the 20 Oct 2026 snapshot. These observations cover only those specific site/location contexts,
not every Nairobi branch. Carrefour's later location-selection attempt did not reliably confirm its
backend delivery area, so its example remains explicitly dated to the earlier Westlands snapshot.
The notes are reference evidence for human review, not human-authored answers or a branch-complete
price dataset.

The market-price draft questions focus on Nairobi, Mombasa, and Kisumu. Coverage is limited:
Kisumu has no price observations, Nairobi and Mombasa have no maize observations, and their bean
observations are old. Review expected answers against the current data rather than implying current
prices where none are available.

Only after human review, copy approved rows to `human_test_questions.csv` with `question` and
`expected_intent` columns. The training script evaluates that file as a separate held-out source;
it does not use it to train or tune the model. Do not report the draft's model score as human
evaluation.

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
- The Carrefour supermarket example comes from the 20 Oct 2026 snapshot; the Naivas, Quickmart,
  and Jaza examples were observed on 16 Nov 2026. Re-check names and prices against the source before
  using them as evaluation questions.
- County coverage notes (which county has maize, beans or goat data) come from the RTFP file in the repo; the generator should read the real coverage instead of trusting these notes.
- Goat prices are per unit, not per kg; confirm in the data dictionary before writing answer templates.
- Swahili and sheng-style phrases were written to be simple and natural; have a Swahili speaker skim them.
