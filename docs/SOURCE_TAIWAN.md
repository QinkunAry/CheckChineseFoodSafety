# Taiwan TFDA border noncompliance source assessment

## Decision

Taiwan TFDA is a strong read-only `prototype`. Its official open dataset covers
noncompliant imported food and related products and exposes an explicit `產地`
field. No origin inference or cross-dataset join is required.

## Official resources

- Dataset metadata: <https://data.gov.tw/dataset/6133>
- JSON: <https://data.fda.gov.tw/data/opendata/export/52/json>
- Human search: <https://www.fda.gov.tw/UnsafeFood/UnsafeFood.aspx?idx=0>

The metadata lists origin, subject, reason, importer, tariff code, inspection
method, detailed finding, legal limit, manufacturer/exporter, disposition,
release date and acceptance date. It uses Taiwan's Open Government Data License
1.0, is free, and has an irregular update frequency.

## Live result (2026-06-28 JST)

- total records: 2,472;
- date range: 2023-01-03 through 2026-06-23;
- explicit `中國大陸` or `中國` records: 576;
- likely human-food and food-additive records: 2,183;
- likely China-origin human-food and food-additive records: 388.

Human-food scope is a deterministic project filter: tariff chapters 01–24 are
included, chapter 23 animal feed is excluded, and records whose reason explicitly
identifies food-contact containers/utensils are excluded. Four reviewed tariff
prefixes outside chapters 01–24 cover observed food additives or processing aids:
`2836.30`, `3203.00`, `3301.90`, and `3802.90`.

The first candidate review found and corrected three issues: four food-additive
records were initially excluded, five empty-capsule records were too broadly
labelled as bakery products, and ten chemical findings were unclassified. The
corrected full batch contains 388 candidates with no unclassified hazard tags.

## Probe, inventory and candidate workflow

```powershell
python -m food_safety_watch probe-taiwan-tfda --min-records 2000 --min-china-records 300 --report reports/taiwan_tfda_probe.json
python -m food_safety_watch inventory-taiwan-tfda --state data/state/taiwan_tfda_record_ids.json --report reports/taiwan_tfda_inventory.json
python -m food_safety_watch candidate-taiwan-tfda --state data/state/taiwan_tfda_record_ids.json --output data/candidates/taiwan_tfda_cn.jsonl --report reports/taiwan_tfda_candidates.json
```

The probe validates required fields, dates, stable project IDs, duplicate IDs,
minimum total count and minimum China-origin count. The committed baseline uses
the canonical full-record SHA-256 because TFDA does not publish a native row ID.
Consequently, an official correction appears as one removed hash and one new
hash; this is deliberately surfaced for human review rather than silently
treated as an in-place update.

The candidate command normally selects only hashes absent from the baseline,
requires explicit China origin and the deterministic human-food scope, maps the
records to the shared schema, and writes ignored JSONL plus a quality report.
`--include-current` is an explicit manual-review mode that builds the full
current candidate batch; scheduled runs never enable it automatically.

The first baseline was created on 2026-06-28 from 2,472 official records and is
stored at `data/state/taiwan_tfda_record_ids.json`. A maintainer should update
it only after reviewing the corresponding inventory and candidate artifacts.

`.github/workflows/probe-taiwan-tfda.yml` downloads one consistent snapshot,
runs probe, inventory and candidate steps manually and weekly with
`contents: read`, writes a Job Summary and uploads diagnostic/candidate
artifacts. It never commits or publishes processed data.

## Before candidate publication

- confirm the corrected 388-record batch in GitHub Actions with
  `--include-current`;
- document the baseline acceptance process after reviewed incremental records;
- finalize attribution wording and retain the official dataset/search links.

The initial review record is
[`reviews/TAIWAN_TFDA_INITIAL_CANDIDATE_REVIEW.md`](reviews/TAIWAN_TFDA_INITIAL_CANDIDATE_REVIEW.md).
