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
- likely human-food records: 2,179;
- likely China-origin human-food records: 384.

Human-food scope is an initial deterministic project filter: tariff chapters
01–24 are included, chapter 23 animal feed is excluded, and records whose reason
explicitly identifies food-contact containers/utensils are excluded. This rule
must be reviewed before candidate publication.

## Probe and workflow

```powershell
python -m food_safety_watch probe-taiwan-tfda --min-records 2000 --min-china-records 300 --report reports/taiwan_tfda_probe.json
```

The probe validates required fields, dates, stable project IDs, duplicate IDs,
minimum total count and minimum China-origin count. It stores short China and
non-China samples in an ignored report and publishes no data.

`.github/workflows/probe-taiwan-tfda.yml` runs manually and weekly with
`contents: read`, writes a Job Summary and uploads the diagnostic report.

## Before candidate publication

- review tariff-based food/non-food exclusions against a larger sample;
- design an incremental baseline despite the dataset lacking a native row ID;
- confirm stable-ID collision behavior when TFDA corrects existing rows;
- implement normalized candidate JSONL and schema validation;
- finalize attribution wording and retain the official dataset/search links.
