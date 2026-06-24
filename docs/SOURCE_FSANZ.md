# FSANZ source assessment

## Decision

Food Standards Australia New Zealand (FSANZ) is the preferred second-source
prototype. It exercises a different regulatory action (`recall`) from FDA import
refusals and exposes recall detail URLs through its official sitemap.

The source is **not yet enabled for automated publication**. A live end-to-end
sample passed on GitHub Actions on 2026-06-22. Production status still requires
coverage assessment and confirmation of the site's reuse terms.

## Official endpoints

- Recall landing page: <https://www.foodstandards.gov.au/food-recalls>
- Recall list: <https://www.foodstandards.gov.au/food-recalls/recalls>
- Sitemap: <https://www.foodstandards.gov.au/sitemap.xml>
- Detail prefix: `https://www.foodstandards.gov.au/food-recalls/recall-alert/`

The former `/industry/food-recalls/recalls` route now returns 404 and must not be
used by new code.

## Evidence and filtering rules

- Discover detail URLs only from the official sitemap.
- Accept only HTTPS detail URLs on `www.foodstandards.gov.au`.
- Include a record only when the detail page's explicit `Country of origin`
  field names China, the People's Republic of China, or PRC.
- Never infer Chinese origin from a Chinese-sounding product name, cuisine,
  importer name, or URL slug.
- Preserve the official `Problem` and `Food safety hazard` text as reasons.
- Treat a recall as a recall; do not merge its meaning with an import refusal.

## Availability findings (2026-06-21)

- The official sitemap was accessible and contained recall detail URLs.
- The current recall landing route and detail route are present in the sitemap.
- New Zealand MPI's recall pages returned an Incapsula challenge in the same
  source spike, so MPI is deferred rather than bypassed.
- Repeated live FSANZ detail/API requests from the local development environment
  timed out, but the GitHub Actions smoke workflow successfully validated the
  parser against current official details on 2026-06-22.

## Production gate

1. Parse at least three current official details, including one explicit China
   origin and one non-China origin.
2. Verify publication date, title, problem, hazard, and origin extraction.
3. Run all normalized records through `record.schema.json`.
4. Add baseline-count and count-drop protection for this source.
5. Confirm reuse/attribution requirements.
6. Only then add a publishing workflow and mark the source `implemented`.

## Read-only smoke workflow

`.github/workflows/smoke-fsanz.yml` runs weekly and on manual dispatch. It reads
the official sitemap plus fixed recall details, verifies their evidence-field
structure, validates any China-origin records against the shared schema, and
uploads `fsanz_smoke.json` even when the smoke command fails. A zero-China
result is reported but does not mean the source structure is broken. It has
only `contents: read` permission and never publishes source data.

## Incremental URL baseline

`data/state/fsanz_recall_urls.json` records the 345 recall-detail URLs present in
the official sitemap at baseline creation on 2026-06-22. `inventory-fsanz`
compares the current sitemap with this state and reports additions and removals.
It does not infer origin and does not publish recall records. The initial
baseline intentionally avoids re-requesting every historical detail each week;
historical backfill remains a separate, rate-limited task.

## Candidate records for new URLs

`candidate-fsanz` reads the same sitemap and baseline, fetches only newly
discovered detail URLs, and emits candidate normalized records plus a diagnostic
report. Non-China pages are recorded in the report as `parsed_non_china`; pages
with explicit China origin become JSONL candidate records. Parse failures are
blocking because they indicate either page drift or an evidence field that needs
manual review.

Candidate output is not a production release. The workflow uploads
`data/candidates/fsanz_cn.jsonl` and `reports/fsanz_candidates.json` as artifacts
for review, without changing the baseline or committing FSANZ records.

## Reuse review

The official copyright policy is registered at
<https://www.foodstandards.gov.au/legal-policies/copyright>. Until its applicable
licence and attribution wording are fully recorded, the project takes the
conservative path: no page images or full HTML mirrors, only normalized facts,
short official reason text, and direct source links. This review remains a
production blocker rather than an assumed permission.
