# Prototype to implemented source checklist

This checklist defines the minimum review required before a source can move
from `prototype` to `implemented` and before its records can be published under
`data/processed/`.

The goal is to prevent a source from becoming "implemented" merely because the
parser works once. A source is implemented only when it is legally safe,
operationally stable, and reviewable by a human maintainer.

## 1. Scope and source identity

- [ ] The source is registered in `data/sources.json`.
- [ ] The source has a dedicated `docs/SOURCE_*.md` assessment.
- [ ] The official authority, region, action type, homepage, discovery endpoint,
      and detail URL pattern are documented.
- [ ] The regulatory action is mapped correctly, for example
      `import_refusal`, `recall`, or `safety_alert`.
- [ ] The source's inclusion and exclusion rules are explicit.

## 2. Reuse, copyright, and attribution

- [ ] The official reuse, copyright, licence, or terms page has been located.
- [ ] The applicable licence or reuse wording has been summarized in the source
      assessment.
- [ ] Required attribution wording is documented.
- [ ] The project records whether normalized facts, short reason text, source
      links, full HTML, images, or attachments may be redistributed.
- [ ] If terms are unclear, the source remains `prototype` and publishes no
      processed data.
- [ ] The implemented workflow does not store or publish full page HTML unless
      the source terms explicitly allow it.

## 3. Discovery and incremental coverage

- [ ] The discovery mechanism is official and documented, such as a ZIP, sitemap,
      RSS feed, API, or official yearly index.
- [ ] The parser accepts only official HTTPS hosts and expected URL patterns.
- [ ] A URL or record baseline exists under `data/state/`.
- [ ] The baseline includes a creation date and count in the source assessment.
- [ ] The inventory command reports current count, baseline count, new URLs, and
      removed URLs.
- [ ] Historical backfill scope is documented separately from ongoing monitoring.
- [ ] The source has a plan for how the baseline is updated after reviewed
      candidates are accepted.

## 4. Field evidence and normalization

- [ ] At least two explicit China-origin records and one non-China record have
      passed live smoke validation.
- [ ] Origin is taken only from an explicit official field; it is never inferred
      from product name, cuisine, importer, brand, or URL.
- [ ] Title or product name extraction is validated.
- [ ] Event date extraction is validated and normalized to ISO `YYYY-MM-DD`.
- [ ] Official reason or hazard text extraction is validated.
- [ ] Authority, authority region, source record ID, source URL, and retrieval
      timestamp are populated.
- [ ] Product category and hazard tags are deterministic project labels, not
      presented as official classifications unless the authority supplies them.
- [ ] The parser handles one known non-China page without creating a record.

## 5. Candidate review

- [ ] A candidate command exists and writes JSONL plus a diagnostic report under
      ignored candidate/report paths.
- [ ] The candidate command fetches only new or scoped records, not the entire
      historical archive by accident.
- [ ] Candidate output is uploaded as a workflow artifact.
- [ ] At least one candidate batch has been manually reviewed.
- [ ] Review confirms that every published record links back to an official
      detail page or official dataset.
- [ ] Review confirms that rejected non-China pages are correctly excluded.
- [ ] Review confirms that parse failures block publication and are visible in
      the report.

## 6. Data quality gates

- [ ] Every candidate record validates against `schemas/record.schema.json`.
- [ ] IDs are stable and duplicate-free.
- [ ] Required fields have no unexpected empty values.
- [ ] The source has a minimum expected record count for production publishing,
      or a documented reason why zero records is acceptable for a run.
- [ ] The source has baseline-count or count-drop protection appropriate to its
      update model.
- [ ] The quality report includes record count, duplicate count, schema errors,
      event date range, product category counts, and hazard tag counts.
- [ ] Tests cover successful parsing, non-China exclusion, missing critical
      fields, invalid official URL rejection, inventory changes, and candidate
      parse failures.

## 7. Automation and failure handling

- [ ] The read-only smoke workflow has passed on GitHub Actions.
- [ ] The inventory step has passed on GitHub Actions.
- [ ] The candidate step has passed on GitHub Actions.
- [ ] The future publishing workflow is separate from smoke and candidate
      workflows.
- [ ] The publishing workflow fails closed: it must not overwrite existing
      published data when fetch, parse, schema, or quality checks fail.
- [ ] Failure artifacts include enough information to diagnose source drift
      without publishing failed data.
- [ ] A maintainer notification path exists, such as an issue or workflow summary.
- [ ] Recovery behavior is documented.

## 8. Publication, rollback, and status change

- [ ] The output path under `data/processed/` is documented.
- [ ] The source-specific quality report path under `reports/` is documented.
- [ ] The first production publish is reviewed as a pull request or manual
      commit before enabling automatic commits.
- [ ] The rollback plan is documented: revert the data commit, restore the prior
      baseline if needed, and keep the failed artifact for diagnosis.
- [ ] `data/sources.json` is changed from `prototype` to `implemented` only in
      the same commit or pull request that adds the production publishing gate.
- [ ] `README.md` and the source assessment both describe the source as
      implemented only after the production workflow exists and passes.

## Current source status

| Source | Status | Implemented blockers |
| --- | --- | --- |
| FDA Import Refusals | `implemented` | Existing production source. |
| FSANZ Recalls | `prototype` | Reuse terms, reviewed candidate batch, production quality gate, publishing workflow. |
| Hong Kong CFS Alerts | `prototype` | Prior written authorization or equivalent reuse basis, reviewed candidate batch, production quality gate, publishing workflow. |
| Canada Recalls and Safety Alerts | `candidate` | Explicit country-of-origin evidence, broader detail-page sampling, smoke workflow, prototype gate. |
| Japan CAA / MHLW Recalls | `prototype` | Final PDL attribution wording, reviewed non-empty candidate batch, production quality gate, publishing workflow. |
| Korea Food Safety Korea | `candidate` | Second explicit China-origin live sample, fixed smoke set, production access decision (registered `I0490` API vs portal endpoint), inventory design. |
| Taiwan TFDA | `candidate` | Source spike not started; food recall/alert dataset, origin evidence, reuse terms. |
| EU RASFF | `candidate` | API guide/endpoint confirmation, live sample payload, field mapping, smoke workflow, prototype gate. |
