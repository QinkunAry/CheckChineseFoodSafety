# China SAMR initial candidate review

## Review status

`conditionally_passed` for parser structure; source remains `candidate`.

The local candidate parser correctly groups physical worksheet rows into
sampling events and validates them against the shared schema. This review does
not authorize publication. Official workbooks, candidate JSONL and copied
reason text remain local because SAMR reuse terms are not yet sufficiently
clear for redistribution.

## Reviewed notices

1. Direct-XLSX packaging:
   <https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/spcjs/art/2026/art_90d83f2e61be4530903dabe5452cb036.html>
2. ZIP-of-XLSX packaging:
   <https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/spcjs/art/2026/art_da0f77d908a54a02a7feb68c5ae46aa5.html>

The direct-XLSX review used the notice's alcohol workbook: 5 physical rows were
grouped into 3 unique sampling numbers. The ZIP review opened 21 workbooks: 73
physical rows were grouped into 46 unique sampling numbers, leaving 27
continuation rows. Both batches had zero duplicate sampling numbers, duplicate
project IDs or schema errors.

## Grouping and date findings

- `抽样编号` is the stable native record identifier.
- A blank sampling-number cell can be a continuation of the current sample.
- The same visible `序号` can reappear in several merged worksheet regions for
  one sample; it does not start a new event unless the sequence or sampling
  number actually changes.
- All failed items, measured values, standards and label requirements are
  retained as one reasons array for the grouped sample.
- Remarks from both `备注` columns are deduplicated and preserved. They can
  contain authenticity disputes or confirmed impersonation of a producer.
- Excel serial dates and text dates are normalized. The live ZIP also contained
  a prefixed value such as `购进日期：2025/4/12`; the date parser was extended to
  extract and normalize that form.

## Scope and origin correction

The review rejected an initially tempting inference: a Chinese value in
`标称生产企业地址` does not always establish Chinese product origin. Some imported
foods list a Chinese importer, distributor or agent in that field. The SAMR
candidate records therefore use:

- `regulatory_scope`: `domestic_market`;
- `market_country`: `CN`;
- `origin_country`: `unknown` unless a future source field supplies explicit
  country-of-origin evidence.

The 46-sample ZIP had 37 rows with a mainland location token in the nominal
producer-address field, but all 46 correctly remain `origin_country: unknown`.
This keeps domestic-market statistics separate from overseas China-origin
statistics and avoids presenting producer/address inference as official origin.

## Candidate quality result

- workbooks: 21;
- physical rows: 73;
- grouped sampling events: 46;
- continuation rows: 27;
- unique sampling numbers: 46;
- duplicate sampling numbers: 0;
- schema errors: 0;
- origin: 46 `unknown`;
- mainland producer-location evidence: 37;
- product categories represented: 14;
- risk labels represented: chemical, microbiological, labeling, adulteration,
  and composition/quality.

The candidate command is intentionally manual and local:

```powershell
python -m food_safety_watch candidate-china-samr --url OFFICIAL_NOTICE_URL --notice-html LOCAL_NOTICE.html --attachment LOCAL_ATTACHMENT.zip --output data/candidates/china_samr_market.jsonl --report reports/china_samr_candidates.json
```

No candidate step is included in the scheduled GitHub workflow.

## Remaining acceptance work

- A maintainer should manually compare a broader sample of grouped rows with
  the rendered official workbooks, especially remarks and multi-failure samples.
- Correction semantics for a sampling number reappearing in an amended notice
  must be defined.
- The project needs a documented reuse decision before any candidate artifact
  or normalized SAMR reason text can be published.
- Product category and risk mappings need broader historical coverage.

Until those checks are complete, the parser result is conditional and SAMR
must remain `candidate`.
