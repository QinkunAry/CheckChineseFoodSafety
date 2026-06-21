# FSANZ source assessment

## Decision

Food Standards Australia New Zealand (FSANZ) is the preferred second-source
prototype. It exercises a different regulatory action (`recall`) from FDA import
refusals and exposes recall detail URLs through its official sitemap.

The source is **not yet enabled for automated publication**. Production status
requires a live end-to-end sample to pass parsing and schema checks on GitHub
Actions, plus confirmation of the site's reuse terms.

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
  timed out. The parser is therefore covered by a representative fixed fixture,
  but its selectors still require validation against a fresh official page.

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
