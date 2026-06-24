# Hong Kong CFS source assessment

## Decision

The Hong Kong Centre for Food Safety (CFS) Food Alerts / Allergy Alerts pages are
the preferred third-source prototype. The source is close to the intended users,
has stable English pages, and exposes product evidence fields directly in HTML
tables.

The source is **not yet enabled for automated publication**. The current scope is
read-only smoke validation against official pages.

## Official endpoints

- Food Alerts / Allergy Alerts index:
  <https://www.cfs.gov.hk/english/whatsnew/whatsnew_fa/whatsnew_fa.html>
- Year archive example:
  <https://www.cfs.gov.hk/english/whatsnew/whatsnew_fa/whatsnew_fa_2025.html>
- Detail prefix:
  `https://www.cfs.gov.hk/english/whatsnew/whatsnew_fa/`

## Evidence and filtering rules

- Discover detail URLs only from official CFS index or year archive pages.
- Accept only HTTPS pages on `www.cfs.gov.hk`.
- Include a record only when the official `Place of origin` field names China or
  a clearly identifiable mainland China province, municipality, autonomous
  region, or equivalent wording.
- Do not infer Chinese origin from brand, cuisine, distributor, importer, or URL.
- Preserve the official `Reason For Issuing Alert` text as reasons.
- Treat CFS food/allergy alerts as `safety_alert`, not import refusals.

## Read-only smoke workflow

`.github/workflows/smoke-cfs.yml` runs weekly and on manual dispatch. It reads
official CFS index pages plus fixed detail pages, verifies title, issue date,
food product, place of origin, and alert reason extraction, and validates
China-origin records against `record.schema.json`.

The workflow has only `contents: read` permission and never publishes CFS data.

## Production gate

1. Run live smoke on at least two China-origin pages and one non-China page.
2. Add an incremental URL baseline for year index pages.
3. Build a candidate-only pipeline before any data release.
4. Confirm applicable reuse and attribution terms.
5. Add baseline-count and count-drop protection.
6. Only then consider adding a publishing workflow and changing status from
   `prototype` to `implemented`.
