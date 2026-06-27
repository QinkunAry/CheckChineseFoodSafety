# Japan CAA / MHLW recall source assessment

## Decision

Japan is a strong next source for the project. The Consumer Affairs Agency
(CAA) recall portal exposes a food category list, and food recall detail pages
often link to the Ministry of Health, Labour and Welfare (MHLW) Food Sanitation
Application System public recall detail.

This source is a **read-only prototype**. It is more promising than Canada for
the China-origin dataset because current live samples include explicit
`中国産` product evidence and stable MHLW recall IDs. It still must not publish
records under `data/processed/` until pagination/inventory, candidate review,
attribution, and production quality gates are complete.

## Official endpoints

- CAA recall portal:
  <https://www.recall.caa.go.jp/>
- CAA food recall list:
  <https://www.recall.caa.go.jp/result/index.php?screenkbn=01&category=1>
- CAA detail pattern:
  `https://www.recall.caa.go.jp/result/detail.php?rcl={CAA_ID}&screenkbn=01`
- MHLW Food Sanitation Application System information page:
  <https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/kenkou_iryou/shokuhin/kigu/index_00012.html>
- MHLW public recall search entry:
  <https://i2fas.mhlw.go.jp/faspub/_link.do>
- MHLW public recall detail pattern:
  `https://i2fas.mhlw.go.jp/faspub/_link.do?i=IO_S020502&p={RCL_ID}`
- MHLW terms / copyright page:
  <https://www.mhlw.go.jp/chosakuken/index.html>
- CAA recall site about page:
  <https://www.recall.caa.go.jp/about/index.php>

## Availability findings (2026-06-25)

- The CAA recall portal is accessible as server-rendered HTML.
- CAA category `1` is `食料品` (food).
- The CAA food list reported 320 food recall entries and rendered 15 entries on
  the first page.
- CAA detail pages expose title, product name, contact, action method, action
  start date, product identification details, notes, and management number.
- CAA detail pages may include `参照情報` links to MHLW public recall details.
- The inspected CAA food detail for management number `00000035456` linked to
  MHLW recall `RCL202601495`.
- The MHLW public detail page is directly accessible and exposes stable hidden
  text fields such as `_rcl_no_str`, `_rcl_product_str`, `_rcl_info_str`,
  `_rcl_rsn_type_str`, `_rcl_rsn_memo_str`, `_sale_sts_str`, `_rcl_date_str`,
  and health-risk fields.
- The MHLW information page states that the system can be used for food business
  applications/notifications and food recall reports, and that public recall
  report information can be checked through the public system.

## Origin evidence probe

`probe-japan-caa` is a read-only diagnostic command. It reads the official CAA
food list, samples recent detail pages, follows MHLW reference links where
present, and counts explicit China-origin evidence.

The command treats `中国産`, `中華人民共和国産`, `原産国：中国`, and `中国製` as explicit
China-origin evidence. It does not treat generic Chinese-style wording as origin
evidence.

Live result on 2026-06-25:

- CAA food list total: 320;
- list entries visible on first page: 15;
- sampled detail pages: 10;
- sampled pages with MHLW reference links: 10;
- sampled pages with explicit China-origin evidence: 1.

China-origin sample:

- CAA management number: `00000035456`;
- CAA title: `マルエツ（春日部緑町店）「うなぎ（宮崎県産）長焼1尾、2尾、中国産うなぎ長焼（特大）1尾、2尾」 - 返金／回収`;
- MHLW recall ID: `RCL202601495`;
- MHLW URL:
  <https://i2fas.mhlw.go.jp/faspub/_link.do?i=IO_S020502&p=RCL202601495>.

Command used:

```powershell
python -m food_safety_watch probe-japan-caa --limit 10 --china-mention-limit 5 --report reports/japan_caa_probe.json
```

## Read-only smoke workflow

`smoke-japan-caa` is the source-health gate for the prototype. It is intentionally
narrow:

- parse the official CAA food recall list and require a minimum total count;
- parse fixed official CAA detail URLs;
- follow MHLW `RCL...` reference links when present;
- require at least one fixed page with explicit China-origin evidence;
- write a diagnostic report only, without publishing normalized data.

Live result on 2026-06-27 JST:

- CAA food list total: 322;
- visible list entries parsed: 15;
- fixed detail pages tested: 1;
- fixed pages with MHLW reference links: 1;
- fixed pages with explicit China-origin evidence: 1.

Command used:

```powershell
python -m food_safety_watch smoke-japan-caa --report reports/japan_caa_smoke.json --min-list-total 100 --min-china-records 1 --min-mhlw-references 1 --url "https://www.recall.caa.go.jp/result/detail.php?rcl=00000035456&screenkbn=01"
```

GitHub Actions workflow:

- `.github/workflows/smoke-japan-caa.yml`;
- weekly read-only run plus manual `workflow_dispatch`;
- uploads `reports/japan_caa_smoke.json` as a diagnostic artifact.

## URL inventory

`inventory-japan-caa` scans the official CAA food recall list across its
server-side form pagination. Page 0 uses the public food list URL, and later
pages submit the same official form fields observed in the site HTML:

- `screenkbn=01`;
- `category=1`;
- `viewCountdden=15`;
- `portarorder=2`;
- `actionorder=0`;
- `pagingHidden={zero_based_page_index}`.

Baseline result created on 2026-06-27 JST:

- reported CAA food recall total during inventory: 321;
- expected/scanned pages: 22;
- unique official CAA detail URLs: 321;
- baseline path: `data/state/japan_caa_recall_urls.json`.

Command used:

```powershell
python -m food_safety_watch inventory-japan-caa --state data/state/japan_caa_recall_urls.json --report reports/japan_caa_inventory.json --accept-current
```

Follow-up verification:

```powershell
python -m food_safety_watch inventory-japan-caa --state data/state/japan_caa_recall_urls.json --report reports/japan_caa_inventory.json
```

Result: `unchanged`, with 321 current URLs, 0 new URLs, and 0 removed URLs.

## Evidence and filtering rules

Before normalized records can be generated:

- include only CAA category `食料品` / MHLW public food recall records;
- prefer MHLW `RCL...` detail pages when a CAA record links to them;
- use CAA management number and MHLW recall ID as stable source identifiers;
- include a China-origin record only when the official title, product field, or
  product-identification field explicitly states `中国産`, `中華人民共和国産`,
  `原産国：中国`, or an equivalent product-of-China phrase;
- never infer origin from Chinese cuisine, Chinese characters, importer name,
  company name, product style, or sales channel;
- preserve CAA and MHLW source URLs in diagnostics and future normalized records.

## Reuse review

MHLW's copyright/terms page states that website content can be used under
Japan's Public Data License 1.0 (PDL 1.0) conditions and requires source
attribution. The CAA recall site about page also references PDL 1.0 conditions
and states that edited/processed information must be marked as edited/processed
and must not be presented as if created by the national government or agency.

Project decision:

- Japan is a read-only `prototype`;
- future publication must include attribution to CAA and/or MHLW, source URLs,
  and wording that normalized data is processed by this project;
- do not publish full HTML, product images, or downloaded attachments until
  their reuse status and necessity are reviewed;
- the source appears legally more tractable than CFS, but it still needs a
  production attribution review before `implemented`.

## Known blockers before candidate records / implementation

- MHLW public search is session/form driven; direct detail pages are stable when
  `RCL...` IDs are known, but discovery still needs design.
- The inventory currently discovers CAA detail URLs; MHLW `RCL...` IDs are
  followed from fixed smoke/detail pages and are not yet inventoried directly.
- At least two China-origin and one non-China live samples should be fixed for
  broader parser regression tests before candidate publication.
- A candidate command does not yet exist.
- Attribution wording under PDL 1.0 must be finalized before publication.

## Implemented gate

Before Japan can move from `prototype` to `implemented`, the project needs:

- candidate JSONL and diagnostic report generation for newly discovered records;
- live smoke samples including at least two explicit China-origin records and one
  non-China food recall;
- unit tests covering list parsing, detail parsing, MHLW hidden-field parsing,
  non-China exclusion, inventory changes, candidate generation, and source-drift
  diagnostics;
- final PDL 1.0 attribution wording in README/source docs/report metadata.

Japan must satisfy the shared
[`prototype` to `implemented` checklist](PROTOTYPE_TO_IMPLEMENTED_CHECKLIST.md)
before any records are published under `data/processed/`.
