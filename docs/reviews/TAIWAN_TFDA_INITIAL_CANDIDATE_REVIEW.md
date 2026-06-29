# Taiwan TFDA initial candidate review

## Review status

`passed` — the corrected local batch passed field and scope review, and the
maintainer subsequently confirmed the GitHub Action passed with
`include_current` after the corrections were committed.

## Reviewed snapshot

- review date: 2026-06-28;
- official records: 2,472;
- explicit China-origin records: 576;
- accepted food / food-additive candidates: 388;
- excluded China-origin food-contact or non-food records: 188;
- candidate date range: 2023-01-03 through 2026-06-23.

## Full-batch checks

- Every candidate `source_record_id` resolves to exactly one official JSON row.
- Every candidate has an explicit China value in the official `產地` field.
- Candidate coverage exactly equals the deterministic China food-scope set.
- Product name, event date, exporter, tariff code, reason and detailed finding
  round-trip to the official row.
- All 388 records validate against `schemas/record.schema.json`.
- Candidate IDs and source record IDs are duplicate-free.
- No candidate uses `other_or_unclassified` after the review corrections.

## Findings corrected during review

1. Four food additives or processing aids were outside tariff chapters 01–24
   and were initially excluded: capsicum colour, sodium bicarbonate, activated
   acid clay and capsicum oleoresin. Their observed tariff prefixes are now an
   explicit narrow whitelist.
2. Five empty-capsule records under tariff `1905.90.10` were initially labelled
   `bakery_and_cereal_products`; they now use `food_capsules`.
3. Ten `其他衛生項目不符規定` records had chemical details such as dioxins,
   PCBs, ethylene oxide, phosphate, chloride or contamination. The deterministic
   chemical vocabulary now covers those findings.

## Corrected category coverage

| Project category | Records |
| --- | ---: |
| vegetables | 100 |
| coffee, tea and spices | 88 |
| seeds and herbs | 74 |
| fruit | 38 |
| prepared fruit and vegetables | 28 |
| seafood | 18 |
| plant extracts | 14 |
| prepared foods | 10 |
| food capsules | 5 |
| prepared meat and seafood | 4 |
| food additives and processing aids | 4 |
| oils and fats | 2 |
| milled grain products | 1 |
| sugar and confectionery | 1 |
| other food | 1 |

## Exclusion review

After the food-additive correction, the 188 excluded China-origin rows are
food-contact articles or non-food related products: 178 explicitly use the
container/utensil migration-test reason, while the remaining ten are packaging
or utensils such as paper boxes, trays and steamer cloth. No observed edible
product remains in the excluded set.

## Production follow-up

Completed: production Action commit `21e8d22` published 388 mutually consistent
records, metadata and a passing quality report. Taiwan TFDA is now an
`implemented` source.
