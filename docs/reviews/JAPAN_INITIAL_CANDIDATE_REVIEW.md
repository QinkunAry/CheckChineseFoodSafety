# Japan MHLW initial candidate review

Status: `one_record_accepted_for_initial_release`  
Reviewed: 2026-07-05

## Evidence reviewed

The GitHub `Smoke test Japan CAA source` workflow passed after explicit review
mode was enabled. Current official CAA and linked MHLW pages were then fetched
again and parsed locally for field-level review.

| CAA ID | MHLW ID | Origin finding | Decision |
|---|---|---|---|
| `00000035456` | `RCL202601495` | One recall covers both Miyazaki-origin and China-origin eel products | Excluded because the current schema would label the whole mixed-origin notice as China |
| `00000035471` | `RCL202601519` | `とんぶり瓶詰（中国産）`; MHLW detail repeats the China-origin product | Accepted |
| `00000035460` | `RCL202601408` | Udon/noodles; no China-origin evidence | Correctly excluded control |

## Accepted record

- Reference: `RCL202601519`
- Product: `とんぶり瓶詰（中国産）`
- Recall event date: `2026-06-12`
- MHLW reason type: `食品衛生法違反のおそれ`
- Reason: off-odour investigation detected spore-forming bacteria
  (`芽胞菌（クロストリジウム属菌）`)
- Project category: `vegetables`
- Project hazard tag: `microbiological`
- Source: official MHLW public detail URL

The MHLW detail also says `輸入食品：いいえ`. This does not negate the explicit
`中国産` product wording; it may describe the regulatory/import handling of the
finished recalled item. The project records only the explicit product-origin
evidence and does not infer the manufacturing chain.

## Publication boundary

- Product, date, origin evidence and reasons in the published row come only
  from MHLW fields.
- CAA is retained as discovery and cross-check evidence in review records, not
  copied into the published reason text.
- The mixed-origin eel notice remains a regression/review sample and is not a
  production China-origin row until product-level origin scope can be
  represented without ambiguity.
- PDL 1.0 attribution, processing and non-endorsement wording is emitted in
  release metadata.
