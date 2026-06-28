# Korea Food Safety Korea recall source assessment

## Decision

Korea has a technically accessible official recall source and at least one live
record whose official product name explicitly states China origin. A read-only
`probe-korea-recalls` command now verifies the source, but Korea remains a
`candidate`, not a `prototype`.

The current portal set contains only one explicit China-origin record, while the
shared prototype gate requires at least two China-origin records and one
non-China control. The project must not infer origin from a Korean importer,
manufacturer, product style, or Chinese-language branding.

## Official endpoints

- Food Safety Korea homepage:
  <https://www.foodsafetykorea.go.kr/>
- Recall and sales-suspension portal:
  <https://www.foodsafetykorea.go.kr/portal/fooddanger/suspension.do?menu_grp=MENU_NEW02&menu_no=2713>
- Portal list endpoint used by the official page:
  `POST https://www.foodsafetykorea.go.kr/portal/fooddanger/searchSuspensionList.do`
- Detail pattern:
  `https://www.foodsafetykorea.go.kr/layer/suspensionDetail.do?search_keyword={RTRVLDSUSE_SEQ}`
- Official OpenAPI service metadata (`I0490`, 회수.판매중지 정보):
  <https://www.foodsafetykorea.go.kr/api/openApiInfo.do?menu_grp=MENU_GRP31&menu_no=661&show_cnt=10&start_idx=1&svc_no=I0490&svc_type_cd=API_TYPE06>
- OpenAPI usage guide:
  <https://www.foodsafetykorea.go.kr/api/howToUseApi.do>

## Availability findings (2026-06-28 JST)

- The public recall portal is server-rendered HTML and then loads records from a
  same-origin JSON POST endpoint.
- The list request accepts page number, page size, search type, and search
  keyword. A page size of 400 returned all 359 current portal records during the
  probe.
- Detail pages are directly readable using a numeric recall/sales-suspension
  sequence (`rtrvldsuse_seq`).
- Detail pages expose product name, registration date, reason, inspection
  authority, recall method, recalling business, business address, barcode,
  package size, recall grade, food category, and recall authority.
- The documented `I0490` OpenAPI is updated continuously and requires a
  registered authentication key. The official guide says registration and login
  are required and keys are issued after application.
- The portal endpoint is useful for a read-only source probe, but it is not the
  documented long-term OpenAPI contract. Production automation should prefer
  `I0490` after the maintainer obtains a key.

## Origin evidence result

The 359 portal records contained:

- 4 product names with explicit country-origin wording recognized by the probe;
- 1 explicit China-origin product;
- 0 non-empty `mnf_natncd` manufacturing-country fields;
- 0 non-empty `incmfood_prdtcd` imported-product codes;
- 0 non-empty `prdlst_report_ledg_no` report numbers usable for a deterministic
  cross-dataset join.

Verified China-origin sample:

- sequence: `3000227626`;
- product: `정성 가득 담은 고춧가루(중국산)`;
- registration date: `2026.06.19`;
- reason: `금속성이물(쇳가루) 기준 규격 부적합`;
- category: `가공식품`;
- detail:
  <https://www.foodsafetykorea.go.kr/layer/suspensionDetail.do?search_keyword=3000227626>.

Verified non-China origin comparison:

- sequence: `3000227684`;
- product: `자연향 가득한 고춧가루 (베트남산)`;
- registration date: `2026.06.22`.

The China sample is manufactured/packed by a Korean business but explicitly
identifies the pepper powder as China-origin. This project records product origin,
not the location of the recalling business.

## Probe command

`probe-korea-recalls` requests up to 400 current portal records, samples the
latest records, adds records whose product names contain explicit country-origin
wording, and validates their official detail pages.

```powershell
python -m food_safety_watch probe-korea-recalls --limit 10 --origin-mention-limit 20 --report reports/korea_recall_probe.json
```

The probe fails closed on malformed list responses, invalid identifiers,
non-official detail URLs, or missing product/date/reason fields. It does not fail
merely because only one China-origin record currently exists; instead, the count
is preserved in the report for the prototype decision.

## Evidence rules

Accepted China-origin evidence is limited to explicit official wording such as:

- `중국산` (product of China);
- `중화인민공화국산`;
- `원산지: 중국`;
- `제조국: 중국`.

The following are not origin evidence:

- `중국식` (Chinese-style);
- a Chinese or Chinese-sounding product name;
- importer, distributor, or business name;
- Korean business address;
- packaging text or images without a corresponding official text field.

## Scope and filtering

The portal includes food, health-functional food, agricultural products,
livestock products, alcohol, seafood, and also non-food contact materials. A
future normalized adapter must explicitly exclude `기구용기포장` and other
non-ingestible categories before publication.

## Reuse and attribution

The official `I0490` metadata marks the service as attribution-required and
permits commercial/non-commercial use and derivative works. Publication should
attribute the Ministry of Food and Drug Safety / Food Safety Korea and retain an
official source URL for every record.

The project will not redistribute product images, full HTML, or attachments.
Because the no-key portal JSON endpoint is an implementation endpoint rather
than the documented OpenAPI contract, Korea remains non-publishing until the
production access method and attribution wording are finalized.

## Blockers before prototype

- A second live recall with explicit China-origin evidence is needed to satisfy
  the shared two-China/one-non-China smoke gate.
- A fixed non-China detail sample must be included alongside the two China
  samples in a GitHub Actions smoke workflow.
- The maintainer must decide whether to register for an `I0490` OpenAPI key or
  obtain confirmation that the portal JSON endpoint is suitable for scheduled
  use.
- Full pagination/inventory behavior and historical coverage must be designed.
- Food/non-food category exclusions need regression fixtures.

Only after these items are complete should Korea move from `candidate` to
`prototype`; candidate JSONL and publication gates come later.
