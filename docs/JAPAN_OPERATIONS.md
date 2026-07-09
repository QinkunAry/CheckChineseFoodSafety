# Japan MHLW release operations / 日本来源运维手册

Status: accepted for implemented source operations
Applies to: `data/processed/japan_mhlw_cn.jsonl` and metadata  
Last reviewed: 2026-07-07

## Invariants

- Published rows are backed by a verified MHLW `RCL...` detail, not CAA-only
  expressive content.
- MHLW itself must provide explicit China-origin product evidence.
- Additions and corrections require an exact `--approved-reference` allowlist.
- Mixed-origin notices remain excluded while the schema has only one
  `origin_country` value.
- CAA inventory state is an append-only set of previously seen URLs. A URL
  leaving the rolling current list is not a withdrawal and is never removed
  from the seen-state baseline.
- Published data and PDL metadata change together; failed pair replacement
  restores the previous pair.

## Normal addition or correction

1. Run `inventory-japan-caa` without `--accept-current`.
2. Generate candidates from new URLs or an explicit bounded `--url` batch.
3. Review CAA discovery evidence and the linked MHLW detail. Reject mixed
   origin, missing MHLW origin evidence, CAA-only text and unclassified hazards.
4. Put only approved MHLW-backed records in the reviewed candidate JSONL.
5. Merge them into the current release:

```powershell
python -m food_safety_watch publish-japan-reviewed `
  --input data/candidates/japan_caa_reviewed.jsonl `
  --output data/processed/japan_mhlw_cn.jsonl `
  --metadata data/processed/japan_mhlw_cn.metadata.json `
  --report reports/japan_mhlw_quality.json `
  --schema schemas/record.schema.json `
  --merge-current `
  --approved-reference RCLYYYYNNNNNN `
  --min-records EXPECTED_MINIMUM `
  --max-records 100 `
  --max-unclassified 0
```

Unmentioned published rows remain unchanged. An approved existing MHLW
reference is replaced as a correction while retaining its first
`retrieved_at`.

6. Inspect JSONL and metadata diffs, run `audit-japan-mhlw`, commit, then run
   `Audit published Japan MHLW records` on GitHub.
7. After review succeeds, accept inventory with `--accept-current`. This adds
   current URLs to the historical seen set and never deletes older seen URLs.

## Official correction or loss of China-origin evidence

An audit `action_required` result freezes publication changes for the affected
reference until a maintainer reviews the MHLW page.

- If corrected fields remain China-origin and in scope, regenerate that one
  reference and publish it through `--merge-current --approved-reference`.
- If MHLW no longer provides China-origin evidence, preserve the audit report
  and Issue, then remove only that published reference:

```powershell
python -m food_safety_watch publish-japan-reviewed `
  --output data/processed/japan_mhlw_cn.jsonl `
  --metadata data/processed/japan_mhlw_cn.metadata.json `
  --report reports/japan_mhlw_quality.json `
  --schema schemas/record.schema.json `
  --merge-current `
  --removal-only `
  --remove-reference RCLYYYYNNNNNN `
  --min-records EXPECTED_REMAINING_COUNT `
  --max-drop-percent EXPLICIT_REVIEWED_LIMIT
```

If the last published row must be removed, explicitly use `--min-records 0`.
The resulting empty release is valid and its audit returns `passed` with a
warning. Never remove a record merely because its CAA URL left the rolling
current list.

## Rollback

- Before commit, pair publication automatically restores the previous JSONL
  and metadata if replacement fails.
- After push, preserve the quality/audit artifact and use
  `git revert <bad-release-commit>`. Do not force-push or use
  `git reset --hard`.
- Push the revert, manually rerun the MHLW audit, and close the maintenance
  Issue only after the hosted audit is green.
- Revert an incorrectly accepted inventory state in the same operation so the
  candidate remains discoverable.

## Human acceptance checklist

- [ ] Candidate batch and approval allowlist match exactly.
- [ ] MHLW ID, URL, product, origin, date and reasons were reviewed.
- [ ] Mixed-origin and CAA-only records are excluded.
- [ ] Quality report passed with zero Schema, duplicate and unclassified errors.
- [ ] Unrelated published rows did not change or disappear.
- [ ] PDL attribution, processing and no-endorsement wording remains intact.
- [ ] Local and hosted published-detail audits passed.
- [ ] Inventory acceptance appended to, rather than replaced, the seen set.
