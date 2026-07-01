# EU RASFF source assessment

## Decision

The European Commission Rapid Alert System for Food and Feed (RASFF) is a
read-only `prototype` source. The live probe passed locally and on GitHub
Actions on 2026-06-30. A complete inventory and minimal fingerprint baseline
now provide incremental change detection without publishing a full API snapshot.

The probe uses the same official public JSON endpoints as RASFF Window. It does
not scrape rendered HTML, require an account, bypass access controls, publish a
historical snapshot, or write records under `data/processed/`.

## Official endpoints

- European Commission RASFF overview:
  <https://food.ec.europa.eu/food-safety/rasff_en>
- RASFF Window search interface:
  <https://webgate.ec.europa.eu/rasff-window/screen/search>
- RASFF Window public configuration:
  <https://webgate.ec.europa.eu/rasff-window/backend/public/configuration/>
- RASFF Window country catalog:
  <https://webgate.ec.europa.eu/rasff-window/backend/public/country/list/>
- RASFF Window product-type catalog:
  <https://webgate.ec.europa.eu/rasff-window/backend/public/productType/list/en/>
- RASFF Window consolidated public search endpoint:
  <https://webgate.ec.europa.eu/rasff-window/backend/public/notification/search/consolidated/en/>
- data.europa dataset page:
  <https://data.europa.eu/data/datasets/restored_rasff~~1?locale=en>
- data.europa dataset metadata API:
  <https://data.europa.eu/api/hub/repo/datasets/restored_rasff>
- DG SANTE developer portal entry:
  <https://developer.datalake.sante.service.ec.europa.eu/api-details#api=c5ad39eb-712e-4cb4-a7f6-764de863ae7e&operation=cc6aab62-bd15-4904-b20d-54551ccb9468>

## Live API findings (2026-06-30)

- RASFF Window itself sends an unauthenticated JSON `POST` request to the
  consolidated public search endpoint.
- Public configuration points `openPortalLink` to the official
  `restored_rasff` dataset on data.europa.
- The country catalog identifies China as ID `5075`, ISO `CN`, and India as ID
  `5118`, ISO `IN`. The probe discovers these IDs at runtime instead of assuming
  the numeric values will never change.
- The product-type catalog identifies human food as ID `283`. Feed, animals,
  food-contact materials and other products are excluded.
- The China-plus-food query returned 1,211 records. The India-plus-food control
  returned 2,083 records.
- Ten requested China samples were all type `food` and contained explicit `CN`
  entries in `originCountries`. Two India controls contained only `IN` evidence
  and emitted no normalized China record.
- The response exposes `notifId`, `reference`, `ecValidationDate`, `subject`,
  notifying country, product category, product type, classification, risk
  decision and origin countries.
- The response has no separate clean product-name field. The probe preserves the
  official notification subject as both `product_name` and `reasons` rather than
  heuristically deleting hazard wording.

These counts are dated diagnostics, not permanent dataset guarantees.

## Evidence and filtering rules

RASFF contains both food and feed notifications. The probe:

- includes only records whose official `originCountries` contains ISO `CN`;
- includes only records whose official product type is exactly `food`;
- never infers origin from cuisine, brand, product wording, exporter, importer,
  notifying country or free-text narrative alone;
- preserves the official RASFF reference as `source_record_id` and links to the
  official notification route;
- maps the event date from `ecValidationDate` and preserves the official product
  category description;
- uses the distinct `rasff_notification` action type because results may be
  alerts, border rejections or information notifications;
- treats project hazard tags as search aids, not official classifications.

## Reuse review

The data.europa metadata identifies the RASFF Window distribution, API user guide
distribution, JSON API distribution, and pre-2021 XLSX resource as
`CC_BY_4_0`.

Project decision:

- RASFF is a read-only `prototype`; no processed records are published;
- any future publication must include attribution to the European Commission /
  DG SANTE / RASFF and direct source links;
- before publishing normalized records, exact attribution wording and any
  endpoint usage limits must be recorded;
- do not commit scraped RASFF Window HTML or JavaScript as project data.

The API guide download still returns 404. This is a documentation concern but no
longer blocks a minimal health probe because the official public endpoint,
catalogs, request shape and live fields have now been verified. The probe stores
only minimal diagnostics and samples, not full HTML, JavaScript or API snapshots.

## Probe and quality gate

Run locally with:

```powershell
python -m food_safety_watch probe-rasff `
  --schema schemas/record.schema.json `
  --report reports/rasff_probe.json `
  --min-china-food-records 1000 `
  --sample-size 10
```

The command dynamically resolves the country and product-type IDs, runs a China
human-food query and an India human-food control, normalizes the China samples,
and validates them against `record.schema.json`. It fails closed on catalog or
field drift, out-of-scope product types, missing China origin, control leakage,
count-floor failure, duplicates or Schema errors.

The 2026-06-30 local live run passed with 1,211 China human-food records reported
by the API, ten normalized samples, two India controls, zero false China
emissions, zero Schema errors and zero duplicate IDs. Sample event dates ranged
from 2026-06-19 through 2026-06-26.

The same probe subsequently passed on GitHub Actions, satisfying the hosted
runner acceptance gate.

## Complete inventory and baseline

`inventory-rasff` uses the same runtime-discovered China and food IDs and reads
all result pages with a maximum page size of 100. It fails closed when:

- `totalElements` or `totalPages` changes during a scan;
- reported pages do not match the total and requested page size;
- a full page has an unexpected record count;
- any page contains a non-China or non-food record;
- notification IDs or official references are duplicated;
- the final unique record count does not equal the reported total.

The baseline under `data/state/rasff_notification_ids.json` does not contain
subjects or full records. Each entry stores only the official numeric
notification ID, official reference and a SHA-256 fingerprint of selected
public fields. This supports three diagnostics:

- a new reference is a newly observed notification;
- a missing reference is a removed or no-longer-returned notification;
- a changed fingerprint means selected public fields changed and requires human
  review; it does not automatically define the legal correction semantics.

The initial 2026-06-30 complete scan covered 13 of 13 pages and 1,211 of 1,211
China-origin human-food notifications. An immediate second complete scan against
the new baseline returned `unchanged`: zero new, zero removed and zero changed.
Observed references span 2018 through 2026 (4 from 2018 and 12 from 2019), even
though the public documentation describes the normal public-search scope as 2020
onward. The project therefore records the live API result but does not claim
complete pre-2020 historical coverage.

Run the inventory with:

```powershell
python -m food_safety_watch inventory-rasff `
  --state data/state/rasff_notification_ids.json `
  --report reports/rasff_inventory.json `
  --page-size 100
```

`--accept-current` may replace the baseline only after a complete successful
scan. A failed or `--max-pages` partial scan is refused.

## Prototype to implemented gate

Before moving from `prototype` to `implemented`, the project must add a reviewed
candidate batch, final CC BY 4.0 attribution, a decision about the combined
subject/product field, publication count-drop and atomic-write gates, explicit
correction/removal handling, maintainer notification and rollback documentation.

## Local candidate pipeline and initial review

`candidate-rasff` performs a complete inventory and then selects only references
that are new or whose selected-field fingerprint changed since the baseline.
For a bounded manual review, repeated `--reference` arguments select explicit
current records. `--max-candidates` fails the batch before writing partial output
when an unexpected number of records is selected.

Candidate JSONL and reports are ignored local artifacts. They are not part of
the scheduled workflow because publication rights and field semantics are still
under review.

The first review covered five recent explicit references and the first real
post-baseline increment, `2026.5752`. All six passed explicit China origin,
human-food scope, stable-ID and Schema checks. Publication remains blocked:

- the public search `subject` combines product, finding and regulatory action;
- `2026.5752` has subject `Consignment possibly subject to veterinary checks`,
  which contains no identifiable product;
- notification classification and risk decision need dedicated production
  fields rather than being hidden in diagnostic output;
- generic project hazard rules leave most reviewed RASFF subjects unclassified;
- one pepper-powder subject has an official search category of nuts/seeds and
  requires detail-level verification rather than heuristic correction.

See the full review:
[`RASFF_INITIAL_CANDIDATE_REVIEW.md`](reviews/RASFF_INITIAL_CANDIDATE_REVIEW.md).

## Official notification detail

RASFF Window loads public notification details from:

`GET https://webgate.ec.europa.eu/rasff-window/backend/public/notification/view/id/{notification_id}/en/`

Live checks on 2026-07-01 confirmed that detail JSON supplies:

- an independent `product.description` suitable for `product_name`;
- product category and product type;
- hazards with name, official category, analytical result, unit, sampling date
  and maximum permitted level where available;
- notification basis, classification, risk decision and status;
- distribution status, measures and last-update timestamp;
- organization flags that distinguish origin, notifying, distribution and
  operator countries;
- follow-ups including corrigenda and withdrawal actions.

The detail-enriched incremental candidate for `2026.5752` now correctly uses
`Vermicelli` as its product name while retaining the original procedural subject
as the reason because no hazard is listed. A China hazard sample exposes
`Aflatoxin B1 - mycotoxins`; an India rice/pesticide detail is excluded by its
official `IN` origin flag.

The new `smoke-rasff-detail` command fixes two active China details—one no-hazard
sample and one hazard sample—plus one India control. It validates normalized
China records against the shared schema. The scheduled RASFF Action now runs
this detail smoke after the public search probe and complete inventory.

One separately reviewed China detail, `2026.5575`, is `ec_withdrawn` even though
the consolidated search result did not expose that status. Therefore search
inventory alone is insufficient for production correction handling. RASFF stays
`prototype` until the project defines detail-status rechecks, withdrawal and
corrigendum semantics.

## Lifecycle decision

The project now separates technical candidate success from lifecycle
eligibility:

- official `ec_validated` with no withdrawal follow-up maps to project
  `record_status: active`;
- official `ec_withdrawn` maps to `record_status: withdrawn` and remains
  auditable rather than being silently deleted;
- an unknown official status, or a contradictory validated record carrying a
  withdrawal follow-up, maps to `record_status: review_required`;
- a corrigendum follow-up alone does not withdraw a currently validated record.

Candidate reports include counts for all three states and a separate
`lifecycle_gate_status`. Technical parsing may pass while the lifecycle gate is
blocked. Only an all-active detail-enriched batch can pass that gate; this does
not by itself satisfy licence, human-review or production-publication gates.

Real verification:

- `2026.5752` is `ec_validated`, has a `corrigendum` follow-up and maps to
  `active`;
- `2026.5575` is `ec_withdrawn`, has request/withdrawal follow-ups and maps to
  `withdrawn`.

Production still needs a periodic detail-status audit for every published RASFF
reference. Search fingerprints cannot substitute for that audit because search
does not expose final notification status.

RASFF must satisfy the shared
[`prototype` to `implemented` checklist](PROTOTYPE_TO_IMPLEMENTED_CHECKLIST.md)
before any records are published under `data/processed/`.
