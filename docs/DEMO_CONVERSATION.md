# Multi-turn assistant demo

Real output of `python scripts/evaluate_dialogues.py`, run on 23 Nov 2026 against the locally trained assistant and the listing snapshot dated 2026-10-20. Answers are copied from that run; nothing is estimated. Where a long list of results is shortened, the transcript says so with "(… N more listings)".

The conversations are the AI-written scripted dialogues (`dialogues_eval.json`), not human-written ones. This is a scripted replay, not a live user session. Advertised prices may differ in store.

**Result of the run:** turn accuracy 0.9462 (88/93); dialogue success 0.9000 (27/30).

---

## 1. Price lookup, store follow-up, "show more", "why?" (eval_01)

1. **User:** Where is the cheapest milk?
   **Assistant:** Carrefour UHT Whole milk 500ml: KES 65 at Carrefour (500ml; KES 130 per l). https://www.carrefour.ke/mafken/en/uht-milk-full-fat/carrefour-uht-whole-milk-500ml/p/247170 Advertised prices, snapshot 2026-10-20, may differ in store.
2. **User:** and at Naivas?
   **Assistant:** No matching advertised listing was found at Naivas in this snapshot. Advertised prices, snapshot 2026-10-20, may differ in store.
3. **User:** show more
   **Assistant:** Ilara Fresh Full Cream Whole Milk 500Ml: KES 68 at Quickmart (500Ml; KES 136 per l). https://www.quickmart.co.ke/ilara-fresh-full-cream-whole-milk-500ml-66 Brookside UHT Whole Milk 250ml: KES 46 at Carrefour (250ml; KES 184 per l). https://www.carrefour.ke/mafken/en/uht-milk-full-fat/brookside-uht-whole-milk-250ml/p/43277 (… 2 more listings) Advertised prices, snapshot 2026-10-20, may differ in store.
4. **User:** why?
   **Assistant:** I compared the available records using the dataset's listed price or unit-price method. Advertised prices, snapshot 2026-10-20, may differ in store.

*Shows:* slot carry-over (the product stays "milk" when the store changes), an honest "not found" instead of a guess, pagination, and an explanation turn.

## 2. Comparing two stores for one product (regression_store_comparison_context)

1. **User:** how much is Brookside UHT whole milk 250ml at Quickmart
   **Assistant:** Brookside Uht Whole Milk 250Ml: KES 47 at Quickmart. https://www.quickmart.co.ke/brookside-uht-whole-milk-250ml Advertised prices, snapshot 2026-10-20, may differ in store.
2. **User:** and at Carrefour?
   **Assistant:** Brookside UHT Whole Milk 250ml: KES 46 at Carrefour. https://www.carrefour.ke/mafken/en/uht-milk-full-fat/brookside-uht-whole-milk-250ml/p/43277 Advertised prices, snapshot 2026-10-20, may differ in store.
3. **User:** which is cheaper?
   **Assistant:**
   Quickmart: Brookside Uht Whole Milk 250Ml, KES 47, 250Ml; KES 188 per l; https://www.quickmart.co.ke/brookside-uht-whole-milk-250ml
   Carrefour: Brookside UHT Whole Milk 250ml, KES 46, 250ml; KES 184 per l; https://www.carrefour.ke/mafken/en/uht-milk-full-fat/brookside-uht-whole-milk-250ml/p/43277
   Carrefour is cheaper by KES 4.00 per l (2.13%).
   Advertised prices, snapshot 2026-10-20, may differ in store.

*Shows:* the comparison uses the two listings already in the dialogue context and computes a unit-price difference.

## 3. Market data across counties, commodities and years (eval_03)

1. **User:** beans price in Kitui
   **Assistant:** 165.34 KES per kg at Kitui (May 2026) Observed coverage: 2007-01-01 to 2026-05-01.
2. **User:** and in Garissa?
   **Assistant:** 119.09 KES per kg at IFO (Daadab) (Aug 2026) Observed coverage: 2018-12-01 to 2026-08-01.
3. **User:** what about maize?
   **Assistant:** 103 KES per kg at Garissa town (Garissa) (May 2026) Observed coverage: 2010-01-01 to 2026-05-01.
4. **User:** and in 2023?
   **Assistant:** 100 KES per kg at Garissa town (Garissa) (Jan 2023) Observed coverage: 2023-01-01 to 2023-01-01.

*Shows:* the dialogue swaps county, commodity and year one slot at a time, and each answer states its observed coverage.

## 4. Missing data is reported, never estimated (eval_12)

1. **User:** beans price in Mombasa
   **Assistant:** 109.33 KES per kg at Bangladesh (Mombasa) (Nov 2021) 93.33 KES per kg at Junda (Mombasa) (Nov 2021) (… 3 more markets) Observed coverage: 2021-01-01 to 2021-11-01.
2. **User:** what about maize?
   **Assistant:** No observations for maize in Mombasa in the dataset.
3. **User:** in 2024?
   **Assistant:** No observations for that county and commodity in 2024.

## 5. Out-of-scope question, then recovery (eval_22)

1. **User:** does it rain tomorrow?
   **Assistant:** I can't answer that from the data I have. Try asking: 'cheapest sugar 2kg?', 'beans price in Kitui', or 'food inflation latest'.
2. **User:** cheapest sugar
   **Assistant:** Naivas Local Sugar White 2Kg: KES 289 at Naivas (2Kg; KES 144.5 per kg). https://www.naivas.online/naivas-local-sugar-white-2kg Advertised prices, snapshot 2026-10-20, may differ in store.
3. **User:** why?
   **Assistant:** Naivas Local Sugar White 2Kg: KES 289 at Naivas. I compared the available records using the dataset's listed price or unit-price method. Sources: Kenya supermarket listing snapshot. Advertised prices, snapshot 2026-10-20, may differ in store.

*Shows:* a refusal with example questions, and a later in-scope question that still works.

## 6. Store not in the snapshot (eval_23)

1. **User:** cheapest cooking oil
   **Assistant:** Fresh Fri Cooking Oil 1Ltr: KES 350 at Naivas (1Ltr; KES 350 per l). https://www.naivas.online/fresh-fri-cooking-oil-1ltr Advertised prices, snapshot 2026-10-20, may differ in store.
2. **User:** at Tuskys?
   **Assistant:** Tuskys is not in the snapshot. Advertised prices, snapshot 2026-10-20, may differ in store.
3. **User:** what about eggs?
   **Assistant:** Isinya Eggs X15: KES 329 at Carrefour (15 Pieces of Eggs; KES 21.9333 per pcs). https://www.carrefour.ke/mafken/en/brown-eggs/isinya-eggs-x15/p/8034 Advertised prices, snapshot 2026-10-20, may differ in store.

---

## Known failures in this run

3 of 30 dialogues failed (5 of 93 turns). They are listed here because the failing turns are part of the evidence for the 0.90 success rate.

| Dialogue | Turn | Expected | What the assistant did |
|---|---|---|---|
| eval_02 | "what about Quickmart?" after a Naivas sugar price | Mention Quickmart in the reply | Repeated the Naivas result and never mentioned Quickmart. |
| eval_07 | "at Tuskys?" after "cheapest bread" | Say Tuskys is not in the snapshot | Asked "Which product or group?" instead. The same question works in eval_23 (section 6), so the follow-up routing is inconsistent. |
| regression_trailing_punctuation | "Isinya eggs at Carrefour'" (stray apostrophe) | A Carrefour egg listing | Fell back to "I can't answer that from the data I have." The next two turns ("and at Naivas?", "and at Quickmart?") then failed because the context was lost. |

Other weak spots that the automatic checks did not flag:
- In eval_14 the "show more" reply was empty apart from the snapshot caveat.
- In eval_16, "others?" after a clarification request returned unrelated discounted items (cookies, a body cream).
- In eval_10, "show more" after a food-inflation answer repeated the same inflation answer.

These match the weaknesses in the follow-up classifier metrics in `AI_REPORT.md` (`show_more` and `new_question` are its weakest labels).