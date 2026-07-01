# EU RASFF initial candidate review

## Review status

`detail_enriched_pipeline_passed_production_blocked` — candidate selection,
origin/product-type scope, detail enrichment and Schema validation work. The
official detail endpoint resolves the product-name and hazard-field blockers,
and the project now has an explicit lifecycle mapping. Production still requires
periodic status rechecks, broader detail coverage, final attribution and
publishing gates.

## Reviewed snapshot

- review date: 2026-07-01 (Asia/Tokyo);
- baseline: 1,211 China-origin human-food notifications;
- current complete inventory: 1,212;
- actual new reference after baseline: `2026.5752`;
- explicitly reviewed recent references: `2026.5655`, `2026.5625`,
  `2026.5575`, `2026.5514`, and `2026.5506`;
- reviewed candidate records: 6 total across the explicit and incremental runs;
- Schema errors: 0;
- duplicate candidate IDs: 0.

Candidate JSONL and diagnostic reports remain ignored local files. They are not
uploaded by the scheduled RASFF workflow.

## Checks that passed

- Every reviewed notification has official product type `food`.
- Every reviewed notification has an explicit `CN` entry in official
  `originCountries`.
- The India control in the probe emits no China candidate.
- Official reference, notification ID, validation date, notifying country,
  product category, notification classification, risk decision and origin list
  are preserved in the diagnostic evidence sample.
- Stable candidate IDs use the official RASFF reference.
- Event dates normalize to ISO `YYYY-MM-DD`.
- Candidate source URLs use the official RASFF Window notification route.
- Default incremental mode selected the single new reference `2026.5752` and
  did not regenerate all 1,211 baseline records.

## Publication blockers found

### 1. Notification subject is not a product name

The consolidated search response exposes `subject`, not a separate product-name
field. Several subjects combine the product, finding and regulatory process:

- `anthraquinone in Pepper Powder from China`;
- `No pre-notification in TRACES (CHED PART I) for Matcha Powder from China`;
- `Consignment fish gelatin skipped veterinary border control`.

The actual new notification `2026.5752` is more decisive: its subject is
`Consignment possibly subject to veterinary checks`, which contains no
identifiable product at all. Mapping this value to `product_name` satisfies the
current JSON Schema but does not satisfy the product's evidence standard.

Decision: keep the current mapping only as a diagnostic prototype. Do not
publish it as a product name.

### Detail follow-up resolution

RASFF Window was subsequently observed requesting the official endpoint:

`GET /rasff-window/backend/public/notification/view/id/{id}/en/`

For `2026.5752`, detail JSON identifies the product as `Vermicelli` while
preserving the procedural subject separately. The candidate parser now requires
detail identity to match the selected search ID/reference and maps
`product.description` to `product_name`.

This resolves the standalone product-name blocker for detail-enriched
candidates. Search-only normalization remains diagnostic and must not be used
for publication.

### 2. Search-level category can look inconsistent

Reference `2026.5575` describes pepper powder while the official search payload
places it in `nuts, nut products and seeds`. The project must preserve and label
this as the official RASFF category; it must not silently "correct" the category
based on product wording. The discrepancy should be checked against official
detail data before publication.

### 3. Classification and risk need explicit fields

RASFF supplies notification classification and risk decision, for example alert
or border-rejection classifications and serious/not-serious decisions. The
shared record schema currently has only the broad project action type
`rasff_notification`, so these official fields survive only in the diagnostic
report. A production mapping needs dedicated optional fields or documented
source metadata; they should not be folded into `reasons`.

Detail follow-up: the shared schema and candidate records now preserve
`official_notification_classification`, `official_risk_decision`,
`official_notification_basis`, `official_notification_status`,
`official_distribution_status`, `official_last_update`, hazards and measures.

### 4. Generic hazard tags are insufficient

The reviewed subjects mostly normalize to `other_or_unclassified`, including
anthraquinone. RASFF-specific hazard category/detail evidence should be used if
the official detail endpoint exposes it. Guessing hazards from product or free
text is not acceptable.

Detail follow-up: `2026.5575` exposes `anthraquinone - pesticide residues`,
analytical result `0,078 mg/kg`, maximum `0,02 mg/kg` and official hazard
category `pesticide residues`; deterministic normalization now labels it
`chemical`. Records with no official hazards retain an empty hazard-detail list.

### 5. Withdrawal and correction policy

The detail endpoint reports `2026.5575` as `ec_withdrawn` and exposes follow-up
type `withdrawal of original notification`. The search inventory did not expose
this status. Production must define whether withdrawn records are excluded,
retained with status, or represented as tombstones, and must recheck detail
status for already published records. This is now the central semantic blocker.

Project decision after hosted detail-smoke acceptance:

- `ec_validated` without withdrawal follow-up maps to `active`;
- `ec_withdrawn` maps to `withdrawn` and remains available for audit;
- unknown or contradictory combinations map to `review_required`;
- a corrigendum alone does not withdraw a validated record;
- candidate technical status is separate from `lifecycle_gate_status`; withdrawn
  or review-required records block that gate.

The remaining blocker is operational: every published reference must have its
detail status rechecked periodically because search fingerprints omit this
field.

## Candidate pipeline decision

The local-only `candidate-rasff` command is accepted as a prototype review tool:

- default mode selects only references that are new or whose selected-field
  fingerprint changed since the baseline;
- `--reference` may select a small explicit current batch for manual review;
- missing or malformed references fail closed;
- `--max-candidates` prevents an unexpectedly large batch from being partially
  emitted;
- a complete consistent inventory is required before selection;
- every selected search result must resolve to a matching official detail ID and
  reference before normalization;
- parse or Schema failures block the batch.

The command is intentionally not added to the scheduled Action and its JSONL is
not uploaded while reuse wording and field semantics remain unresolved.

## Required follow-up

1. Implement a periodic detail-status audit for every published RASFF reference.
2. Review a broader detail-enriched candidate batch across hazard, no-hazard,
   alert, border-rejection and information classifications.
3. Finalize CC BY 4.0 attribution and API-use wording before candidate artifacts
   or processed records are published.
