# EU RASFF initial candidate review

## Review status

`pipeline_passed_publication_blocked` — candidate selection, origin/product-type
scope, normalization and Schema validation work, but the consolidated search
payload does not provide a reliable standalone product name. These records must
not be published under `data/processed/` with the current mapping.

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

### 4. Generic hazard tags are insufficient

The reviewed subjects mostly normalize to `other_or_unclassified`, including
anthraquinone. RASFF-specific hazard category/detail evidence should be used if
the official detail endpoint exposes it. Guessing hazards from product or free
text is not acceptable.

## Candidate pipeline decision

The local-only `candidate-rasff` command is accepted as a prototype review tool:

- default mode selects only references that are new or whose selected-field
  fingerprint changed since the baseline;
- `--reference` may select a small explicit current batch for manual review;
- missing or malformed references fail closed;
- `--max-candidates` prevents an unexpectedly large batch from being partially
  emitted;
- a complete consistent inventory is required before selection;
- parse or Schema failures block the batch.

The command is intentionally not added to the scheduled Action and its JSONL is
not uploaded while reuse wording and field semantics remain unresolved.

## Required follow-up

1. Identify and verify the official public notification-detail JSON request used
   by RASFF Window.
2. Determine whether detail data provides a product name, hazard category,
   hazard detail, action, distribution and useful dates.
3. Add explicit optional schema fields for official RASFF classification and
   risk decision, or document a source-metadata alternative.
4. Re-run this review with at least two detail-enriched China records and one
   non-China control.
5. Finalize CC BY 4.0 attribution and API-use wording before candidate artifacts
   or processed records are published.
