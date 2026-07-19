# EU RASFF source assessment

## Decision

The European Commission Rapid Alert System for Food and Feed (RASFF) is a
read-only `prototype` source. The live probe passed locally and on GitHub
Actions on 2026-06-30. A complete inventory and minimal fingerprint baseline
now provide incremental change detection without publishing a full API snapshot.
The current explicitly reviewed release contains 13 active records, and the
current accepted search baseline contains 1,226 China-origin food-query
references as of 2026-07-12.

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
- Public configuration originally pointed `openPortalLink` to the official
  `restored_rasff` dataset on data.europa. On 2026-07-12 it pointed to the
  official DG SANTE developer portal API-details page instead. The probe accepts
  both official portal-link forms but still rejects unrelated hosts.
- The country catalog identifies China as ID `5075`, ISO `CN`, and India as ID
  `5118`, ISO `IN`. The probe discovers these IDs at runtime instead of assuming
  the numeric values will never change.
- The product-type catalog identifies human food as ID `283`. Feed, animals
  and other non-food product types are excluded. Detail normalization also
  excludes records whose official product category is `food contact materials`,
  because the public search filter can still surface such a record under the
  food product-type query.
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

- RASFF remains a read-only `prototype`;
- published normalized records include attribution to the European Commission /
  DG SANTE / RASFF and direct source links;
- exact attribution wording and endpoint/reuse limits are recorded in release
  metadata and `DATA_ATTRIBUTION.md`;
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

The expanded detail candidate review, CC BY 4.0 attribution review, reviewed
initial processed release, metadata generation, publication count-drop and
atomic-write gates, status-audit integration, correction rehearsal, natural
increment rehearsal and explicit withdrawn-record removal rehearsal are now
complete locally. Before moving from `prototype` to `implemented`, the project
still needs hosted acceptance of the current 13-record audit and maintainer
acceptance of `RASFF_OPERATIONS.md` as the production procedure.

## Local candidate pipeline and initial review

`candidate-rasff` performs a complete inventory and then selects only references
that are new or whose selected-field fingerprint changed since the baseline.
For a bounded manual review, repeated `--reference` arguments select explicit
current records. `--max-candidates` fails the batch before writing partial output
when an unexpected number of records is selected.

Candidate JSONL and reports are ignored local artifacts. They are not part of
the scheduled workflow because publication rights and field semantics are still
under review.

The first, search-only review covered five recent explicit references and the
first real post-baseline increment, `2026.5752`. All six passed explicit China
origin, human-food scope, stable-ID and Schema checks. At that stage it exposed
the following blockers, which were subsequently addressed or qualified by the
official-detail enrichment and expanded review described below:

- the public search `subject` combines product, finding and regulatory action;
- `2026.5752` has subject `Consignment possibly subject to veterinary checks`,
  which contains no identifiable product;
- notification classification and risk decision needed dedicated production
  fields rather than being hidden in diagnostic output;
- generic project hazard rules leave most reviewed RASFF subjects unclassified;
- one pepper-powder subject had an official search category of nuts/seeds and
  required detail-level verification rather than heuristic correction.

See the full review:
[`RASFF_INITIAL_CANDIDATE_REVIEW.md`](reviews/RASFF_INITIAL_CANDIDATE_REVIEW.md).

The expanded review covers ten unique records across all five observed risk
decisions, three notification classifications, structured hazard/no-hazard,
corrigendum and withdrawn cases. After all three post-baseline increments were
detail-reviewed, the inventory baseline advanced from 1,211 to 1,214. See
[`RASFF_EXPANDED_DETAIL_REVIEW.md`](reviews/RASFF_EXPANDED_DETAIL_REVIEW.md).

A later local live run on 2026-07-09 observed 1,223 current China-origin
food-query results versus the 1,214-record baseline: nine new references, zero
removed references and zero changed fingerprints. Detail enrichment passed for
the batch technically, but one new reference, `2026.5818`, exposed official
detail category `food contact materials`. The project treats that as out of
scope for food records and excludes it at detail-normalization time. The
remaining eight references passed explicit candidate review with zero blockers,
zero Schema errors and a passing lifecycle gate. They still require human field
review before any merge into the published release.

On 2026-07-12 a new full scan observed 1,226 current references versus the
1,214-record baseline: 12 new, zero removed and zero changed. `2026.5818`
remained out of scope as `food contact materials`. The other 11 references
passed explicit review with zero blockers, zero Schema errors and a passing
lifecycle gate, then were published through `publish-rasff-reviewed
--merge-current`. The accepted baseline was advanced to 1,226 only after the
14-record published audit passed locally.

On 2026-07-14 the published-record audit reported four changed details. Three
references (`2026.5595`, `2026.5922` and `2026.6070`) remained active and were
rebuilt as explicit corrections. `2026.5888` had changed to `ec_withdrawn` and
was removed from the active release with `--remove-reference`. The resulting
13-record release passed local published-detail audit.

On 2026-07-19 the published-record audit reported six changed details. All six
references (`2026.5595`, `2026.5922`, `2026.5938`, `2026.6040`, `2026.6070`
and `2026.6185`) remained active and were rebuilt as explicit corrections. The
release stayed at 13 active records and passed local published-detail audit.
The same candidate run observed five new search references and one changed
search fingerprint; those were deliberately left for a separate
candidate-review round and did not advance the accepted inventory baseline in
that correction batch.

Later on 2026-07-19, after the 13-record hosted audit recovered, a fresh
incremental candidate scan again reported baseline 1,226, current 1,231, five
new references and one changed search fingerprint. The reviewed batch
(`2026.5595`, `2026.6208`, `2026.6214`, `2026.6241`, `2026.6278` and
`2026.6384`) passed technical, Schema and lifecycle gates. The five new
China-origin food notifications were published together with the already
corrected `2026.5595` search-fingerprint update, expanding the active release
to 18 records. After local published-detail audit passed with 18 audited and
zero changed, the accepted inventory baseline was advanced to 1,231.

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
inventory alone is insufficient for production correction handling; every
published row must remain covered by detail-status audit and explicit
correction/removal workflows.

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

Every published RASFF reference therefore receives a periodic detail-status
audit. Search fingerprints cannot substitute for that audit because search does
not expose final notification status.

## Explicitly reviewed release

The first reviewed subset was published on 2026-07-01 with three active
references: `2026.5752`, `2026.5760` and `2026.5781`. It is deliberately a
small acceptance release, not a claim that all 1,214 inventory entries have
been detail-reviewed or published.

The reviewed subset was expanded on 2026-07-12 to 14 active references after
one correction rehearsal and one natural-increment release. On 2026-07-14 it
was reduced to 13 active references after the official withdrawal of
`2026.5888`, then rebuilt again on 2026-07-19 for six still-active official
detail corrections. A later 2026-07-19 natural-increment review expanded the
release to 18 active references and advanced the accepted inventory baseline to
1,231. It is still a reviewed subset, not a claim that all 1,231 accepted
inventory references have been detail-reviewed or published.

`publish-rasff-reviewed` requires an explicit human-approved reference
allowlist that exactly matches the input JSONL. It then fails closed on Schema
errors, duplicate IDs/references, non-China or non-origin-based records,
non-RASFF actions, non-official detail URLs, missing detail fields, any status
other than active/`ec_validated`, count drops and an excessive batch size.

```powershell
python -m food_safety_watch publish-rasff-reviewed `
  --input data/candidates/rasff_cn.jsonl `
  --output data/processed/rasff_cn.jsonl `
  --metadata data/processed/rasff_cn.metadata.json `
  --report reports/rasff_quality.json `
  --schema schemas/record.schema.json `
  --approved-reference 2026.5752 `
  --approved-reference 2026.5760 `
  --approved-reference 2026.5781 `
  --min-records 3 --max-records 10 --max-drop-percent 25
```

Data and metadata are staged together. If either replacement fails, the pair
is rolled back to the previous release. Metadata records the approval mode,
approved references, release scope, CC BY 4.0 attribution/change statement and
per-record source URL, retrieval time, official last update and lifecycle.

For later updates, `--merge-current` retains all unmentioned published rows,
adds or replaces only the explicitly approved candidate references, and
preserves their first retrieval time. A confirmed withdrawal requires
`--removal-only --remove-reference`; an unknown removal, an overlap between
approval and removal, or an empty operation fails closed. The full operating
and rollback procedure is in
[`RASFF_OPERATIONS.md`](RASFF_OPERATIONS.md).

## Published-record status audit

`audit-rasff-status` reads the published JSONL itself,
extracts each official notification ID from the validated source URL, retrieves
the current detail and compares all publication-relevant fields:

- lifecycle status and official notification status;
- official last update and follow-up types;
- product name/category, reasons and deterministic hazard tags;
- classification, risk, basis and distribution;
- structured hazards and measures.

Outcomes are distinct:

- `passed`: every audited published record still matches official detail;
- `action_required`: detail is valid but the published snapshot is stale, for
  example active→withdrawn or a product/hazard correction;
- `failed`: fetch, identity, origin/scope or input validation failed.

`action_required` is a non-zero CLI result so a future production workflow can
open a maintainer issue and rebuild the full release atomically. The audit never
edits a published row in place.

The command defaults to at most 100 records to avoid silently issuing a large
number of detail requests before an approved batching/rate-limit plan exists:

```powershell
python -m food_safety_watch audit-rasff-status `
  --input data/processed/rasff_cn.jsonl `
  --report reports/rasff_status_audit.json `
  --max-records 100
```

`audit-rasff-status.yml` now runs weekly and on manual dispatch. It uploads the
report on every outcome, opens or updates a maintenance Issue on failure or
`action_required`, closes that Issue after recovery, and never edits the
committed release. The first hosted audit passed after commit `51b1a1b`.

## Approved reuse wording

The Commission legal notice and dataset metadata support CC BY 4.0 reuse of the
EU-owned RASFF material, provided appropriate credit is given and modifications
are indicated. The project will preserve © European Union / European Commission
/ DG SANTE / RASFF attribution, dataset and record links, the CC BY 4.0 link,
the Commission disclaimer/legal-notice link, an explicit description of project
transformations, and a no-endorsement statement.

This review covers normalized facts and short official hazard/reason text. It
does not approve copying HTML/JavaScript/full pages, publishing attachments,
using EU logos or marks, or implying endorsement. The release metadata generator
emits the approved wording beside every RASFF release. See
[`RASFF_REUSE_REVIEW.md`](reviews/RASFF_REUSE_REVIEW.md) and
[`DATA_ATTRIBUTION.md`](DATA_ATTRIBUTION.md).

RASFF must satisfy the shared
[`prototype` to `implemented` checklist](PROTOTYPE_TO_IMPLEMENTED_CHECKLIST.md)
before its status is upgraded from `prototype` to `implemented`.
