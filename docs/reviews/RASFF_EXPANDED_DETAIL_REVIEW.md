# EU RASFF expanded detail candidate review

## Review status

`passed_for_prototype_fields` — official detail enrichment, lifecycle mapping,
incremental selection and candidate quality gates passed across the main
classification/risk combinations. This is not production approval; publication
still requires release automation, status-audit wiring and final maintainer
acceptance of the attribution package.

## Review scope

- review date: 2026-07-01 (Asia/Tokyo);
- baseline before review: 1,211 China-origin human-food notifications;
- current complete inventory: 1,214;
- explicit detail batch: 8 records;
- default incremental batch: 3 records;
- unique reviewed references across both batches: 10;
- Schema errors: 0;
- duplicate candidate IDs: 0.

The explicit batch deliberately included one withdrawn notification. Therefore
its technical status passed while its lifecycle gate correctly reported
`blocked`. The default three-record incremental batch contained only active
records and its lifecycle gate passed.

## Coverage matrix

| Reference | Product | Classification | Risk | Hazard / condition | Lifecycle |
| --- | --- | --- | --- | --- | --- |
| 2026.5752 | Vermicelli | information for attention | not serious | no hazard; border-process subject | active + corrigendum |
| 2026.5760 | Xanthan gum | border rejection | not serious | no hazard | active |
| 2026.5781 | Garlic | information for attention | serious | cadmium / heavy metals | active |
| 2026.5192 | Groundnut kernels | information for attention | potentially serious | Aflatoxin B1 / mycotoxins | active |
| 2026.5575 | Pepper Powder | alert | serious | anthraquinone / pesticide residues | withdrawn |
| 2026.5506 | Other green tea (not fermented) | border rejection | no risk | no hazard; missing pre-notification | active |
| 2026.5450 | Black tea | border rejection | potential risk | pesticide residues | active + corrigendum |
| 2026.5371 | crab-flavoured surimi preparation | border rejection | potential risk | fish DNA / adulteration-fraud | active |
| 2026.5088 | Jelly candy | alert | serious | no structured hazard; official follow-ups | active |
| 2026.4998 | Sichuan pepper | border rejection | potentially serious | multiple pesticide residues | active |

The review covers all five observed risk decisions: `no risk`, `not serious`,
`potential risk`, `potentially serious`, and `serious`. It also covers alert,
border-rejection and information-for-attention classifications; active,
corrigendum and withdrawn lifecycle evidence; structured chemical,
adulteration/fraud and no-hazard details.

## Findings

### Product and reason fields

- `product.description` consistently provides a better product name than search
  `subject`.
- When official hazards exist, their names are used as reasons and full
  analytical fields remain in `official_hazards`.
- When no hazard is listed, the official subject remains the reason/condition;
  it is not presented as a laboratory finding.
- Official product text can contain odd formatting such as `3|kg`; the project
  preserves it rather than silently rewriting evidence.

### Hazard handling

- Official categories deterministically map pesticide residues, mycotoxins and
  heavy metals to project tag `chemical`.
- `adulteration / fraud` plus fish-DNA wording maps to `adulteration`.
- Repeated hazard names are deduplicated only in the human-facing `reasons`
  list. Every structured analytical row remains in `official_hazards`, because
  duplicate names may carry different results.
- No-hazard records remain `other_or_unclassified`; the project does not invent
  a hazard from product wording.

### Official category and lifecycle

- The official detail category for `2026.5575` remains nuts/seeds even though
  the product is Pepper Powder. This confirms the value is official rather than
  a search-parser error. It is preserved with provenance and not heuristically
  corrected.
- `2026.5575` proves withdrawn records can remain searchable. The project keeps
  the record as `withdrawn` for audit while blocking the active lifecycle gate.
- Corrigenda on `2026.5752` and `2026.5450` do not change active status because
  official status remains `ec_validated` and no withdrawal follow-up exists.

## Incremental acceptance

The complete inventory grew from 1,211 to 1,214. Default candidate mode selected
exactly the three new references (`2026.5752`, `2026.5760`, `2026.5781`), and all
three passed detail, Schema and active lifecycle gates. After review, the
inventory baseline was advanced to 1,214. This marks discovery review only; it
does not publish RASFF records.

## Production gate completion

These review-time gates were later completed before RASFF moved to
`implemented`: a fail-closed reviewed release and metadata file, real
published-record status audit with failure Issue handling, atomic update,
count-drop, rollback and correction behavior, CC BY 4.0 attribution beside each
release, and final maintainer acceptance of `RASFF_OPERATIONS.md`.
