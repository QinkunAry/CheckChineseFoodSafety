# RASFF Release Operations / 发布运维手册

Status: accepted for implemented source operations
Applies to: `data/processed/rasff_cn.jsonl` and its metadata  
Last reviewed: 2026-07-19

This runbook defines the only approved paths for adding, correcting, removing
or rolling back published RASFF records. Discovery never authorizes
publication by itself.

## Invariants

- The committed JSONL contains only explicitly reviewed, China-origin,
  human-food records whose project status is `active` and official status is
  `ec_validated`.
- Every reviewed addition or correction must be named with
  `--approved-reference`; the allowlist must exactly match the candidate batch.
- Existing published rows are retained during `--merge-current` unless an
  operator explicitly names them with `--remove-reference`.
- `review_required` is never published or automatically removed.
- Withdrawn records are removed from the active release only after official
  detail evidence and the audit/candidate report have been reviewed.
- Data and metadata are published as one rollback-protected pair. Git history
  is the durable rollback mechanism after a successful commit.
- Inventory state is accepted only after candidate review, release publication
  and status audit succeed.

## Normal addition or active correction

1. Run the complete inventory without `--accept-current`. Confirm it is a
   complete scan and inspect new, changed and removed references.
2. Generate a detail-enriched candidate batch. Use explicit `--reference`
   arguments when reviewing a correction or a bounded group.
3. Review every official detail page and the report. Require:
   China origin, human-food type, identifiable product, source/reference
   agreement, expected classification/risk/hazard fields, technical status
   `passed`, lifecycle gate `passed`, and no Schema or duplicate-ID errors.
4. Merge only the reviewed batch into the committed release:

```powershell
python -m food_safety_watch publish-rasff-reviewed `
  --input data/candidates/rasff_cn.jsonl `
  --output data/processed/rasff_cn.jsonl `
  --metadata data/processed/rasff_cn.metadata.json `
  --report reports/rasff_quality.json `
  --schema schemas/record.schema.json `
  --merge-current `
  --approved-reference YYYY.NNNN `
  --min-records CURRENT_MINIMUM `
  --max-records 100 `
  --max-drop-percent 25
```

For several reviewed rows, repeat `--approved-reference`. A correction with an
existing reference replaces that row; its first `retrieved_at` is preserved.
Unmentioned published rows remain unchanged.

5. Inspect the JSONL and metadata diff. Confirm count, approved batch,
   `release_references`, per-record provenance, event dates, product names,
   hazards and lifecycle.
6. Run `audit-rasff-status` locally when the official host is reachable.
7. After local publication and local status audit pass, run the complete
   inventory with `--accept-current` if the reviewed release covers the
   discovered new/changed references. Commit the release and accepted inventory
   state together when practical; otherwise commit the release first and accept
   the baseline in a follow-up after hosted audit passes.
8. Push and run `Audit published EU RASFF records` on GitHub. Treat any hosted
   failure as a publication freeze until the report is reviewed.

## Withdrawn notification

1. Treat an audit `action_required` result as a publication freeze for that
   reference. Do not edit JSONL manually.
2. Generate an explicit candidate for the reference and inspect the official
   status, follow-up types, last update and source page. A technically valid
   withdrawn candidate is expected to have a blocked lifecycle gate.
3. Preserve the audit/candidate report in the GitHub run artifact or maintenance
   Issue. Record the official withdrawal evidence in the commit/PR description.
4. Remove only the confirmed reference:

```powershell
python -m food_safety_watch publish-rasff-reviewed `
  --output data/processed/rasff_cn.jsonl `
  --metadata data/processed/rasff_cn.metadata.json `
  --report reports/rasff_quality.json `
  --schema schemas/record.schema.json `
  --merge-current `
  --removal-only `
  --remove-reference YYYY.NNNN `
  --min-records EXPECTED_REMAINING_COUNT `
  --max-records 100 `
  --max-drop-percent EXPLICIT_REVIEWED_LIMIT
```

The default 25% drop gate may block removal from a very small release. Raise it
only enough for the reviewed removal and state the reason in the commit. The
new metadata records `removed_references`. Run the hosted audit immediately
after committing.

## Ambiguous correction

If detail maps to `review_required`, identity fields disagree, the official
page is unavailable, or search and detail evidence conflict:

- leave the current committed release unchanged;
- keep/open the maintenance Issue;
- do not accept the inventory baseline;
- obtain a second manual review or wait for the official source to stabilize.

## Rollback

Before a successful publication, the pair writer automatically restores the
previous JSONL and metadata when either replacement fails.

After a release commit has been pushed:

1. identify the last known-good release commit;
2. preserve the failed audit/quality artifact;
3. use `git revert <bad-release-commit>`—never force-push or `git reset --hard`;
4. push the revert and manually run the published-record audit;
5. comment on the maintenance Issue with the revert and audit links;
6. do not close the Issue until the hosted audit is green.

If the bad commit also accepted inventory state, revert that state with the
same commit so the candidate remains discoverable.

## Verified rehearsals

- 2026-07-10: official `official_last_update` drift for `2026.5752` was handled
  as an explicit correction and the release passed published-record audit.
- 2026-07-12: 11 reviewed natural-increment records were merged into the active
  release; `2026.5818` was excluded as `food contact materials`; the accepted
  inventory baseline advanced to 1,226 only after release validation.
- 2026-07-14: `2026.5888` changed to `ec_withdrawn` and was removed from the
  active release while three still-active records were rebuilt as corrections;
  the resulting 13-record release passed local published-record audit.
- 2026-07-19: six still-active records were rebuilt as explicit corrections
  after official detail updates. No baseline was accepted because the same
  candidate run also reported unrelated new/search-changed references needing
  separate review.
- 2026-07-19: after the 13-record hosted audit recovered, five reviewed
  natural-increment records plus the already corrected `2026.5595` search
  fingerprint update were merged into the active release. The release expanded
  to 18 records, local published-record audit passed, and the accepted inventory
  baseline advanced to 1,231.

## Human acceptance checklist

- [ ] Candidate references exactly equal the approval allowlist.
- [ ] Official detail pages were opened and origin/product/lifecycle checked.
- [ ] Candidate technical and lifecycle gates passed, except a documented
      withdrawn record used only as removal evidence.
- [ ] Quality report passed with expected record count and no Schema/ID errors.
- [ ] JSONL and metadata changed together and provenance is complete.
- [ ] No unrelated record disappeared or changed.
- [ ] CC BY 4.0 attribution, modification and no-endorsement text remains.
- [ ] Hosted published-record audit passed after the commit.
- [ ] Inventory baseline was accepted only after publication validation.
