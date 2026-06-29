# China SAMR national sampling source assessment

## Decision

The State Administration for Market Regulation (SAMR) national food-safety
sampling notices are a technically viable `candidate` source. The official
announcement index is machine-readable, individual notices link to XLSX files
or ZIP archives of XLSX files, and the workbooks expose product-level sampling
identifiers and noncompliance evidence.

The source is not yet a `prototype`. Reuse rights for publishing normalized
derivatives need a documented decision, and product-row normalization has not
yet passed candidate review.

This source has a different scope from the project's overseas sources. It
describes national sampling in the Chinese domestic market and must carry a
`domestic_regulatory_scope` label in future records and user-facing statistics.
It must not be mixed silently with overseas import refusals or recalls involving
China-origin products.

## Official resources

- Food sampling department: <https://www.samr.gov.cn/spcjs/index.html>
- Announcement index: <https://www.samr.gov.cn/spcjs/xxfb/index.html>
- Official product-result query: <https://spcjsac.gsxt.gov.cn/>
- Example notice with individual XLSX attachments:
  <https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/spcjs/art/2026/art_90d83f2e61be4530903dabe5452cb036.html>
- Example notice with a ZIP of XLSX attachments:
  <https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/spcjs/art/2026/art_da0f77d908a54a02a7feb68c5ae46aa5.html>
- Website statement:
  <https://www.samr.gov.cn/jg/wzsm/art/2021/art_c30de52ec3264bd29886479e5471dc72.html>

## Discovery result (2026-06-29 JST)

The official announcement page loads its listing from a same-origin CMS JSON
endpoint. The endpoint reported 259 indexed items and exposed normal pagination
metadata. The server returns at most 99 items per request, so the inventory scans
three pages and verifies that their item counts add back to 259. It recognizes
both `通报` and `通告` title forms and found 78 batch-level noncompliance notices
covering 2021 through 2026.

The separate product-result query is not suitable for unattended collection:
its public request flow obtains an image token and requires a slider result.
The project will not automate or bypass that challenge. Discovery therefore
uses the public announcement index and attached official workbooks.

Recent attachment formats vary:

- some notices link to one XLSX per food category;
- some notices link to one ZIP containing the category workbooks.

The probe accepts both forms, validates that URLs remain on the official SAMR
HTTPS host, reads attachments only in runner memory, and publishes only a small
diagnostic JSON report. It does not retain or redistribute official workbooks.

## Workbook evidence

A 2026 notice covering 46 noncompliant batches supplied a ZIP containing 21
XLSX workbooks. All 21 contained the probe's eight core fields:

- nominal producer name;
- sampled business name;
- sample/product name;
- noncompliant item;
- measured value;
- standard value;
- official food subcategory;
- sampling number (`抽样编号`).

Across those workbooks, 73 physical worksheet rows represented 46 unique
sampling numbers. Some samples occupy multiple rows because separate failed
tests are listed on continuation rows. A future normalizer must group or
forward-fill continuation rows by sampling number; it must not publish each
physical row as a separate food event.

Observed workbooks had 16–19 columns. Additional useful fields include producer
and sampled-business addresses, specification, trademark, production date,
shelf life, inspection institution, label requirements and remarks. Remarks can
record authenticity disputes or findings that a named producer was impersonated
and therefore must be preserved as evidence during candidate review.

Excel serial dates must be normalized explicitly. The native sampling number is
the preferred source record ID; category and notice identity should be retained
to guard against unexpected reuse or corrections.

## Probe command and automation

```powershell
python -m food_safety_watch probe-china-samr --max-notices 1 --max-attachments 2 --min-listing-count 100 --min-discovered-notices 2 --min-workbooks 1 --report reports/china_samr_probe.json
```

The command checks the official listing count, discovers batch-notice URLs,
parses one current notice, follows up to two attachment links, opens direct XLSX
or ZIP-contained XLSX files, and fails if any inspected workbook loses a core
field. A ZIP may contain many workbooks; all workbooks inside the selected ZIP
are checked.

`.github/workflows/probe-china-samr.yml` runs the probe manually and weekly with
`contents: read`. It runs the complete unit-test suite, uploads only
structural diagnostic reports, and never commits candidate or processed data.
The initial probe workflow passed on GitHub Actions on 2026-06-30.

The same workflow now runs the complete inventory after the probe:

```powershell
python -m food_safety_watch inventory-china-samr --state data/state/china_samr_notice_urls.json --report reports/china_samr_inventory.json
```

The committed baseline was created on 2026-06-30 after a complete three-page
scan: 259 indexed items, 78 matching batch notices, zero duplicate notice URLs.
It is stored at `data/state/china_samr_notice_urls.json`. A partial scan may be
used for diagnostics, but `--accept-current` refuses to replace the baseline
unless the scan is complete.

## Reuse and publication boundary

The SAMR website statement says site copyright belongs to the site, prohibits
commercial original-form republication and distortion, and requires contacting
the relevant provider before reproducing information supplied by other units.
The government-information rules establish public access but do not, by
themselves, provide a clear open-data licence for republication of normalized
product rows.

Until a defensible reuse basis or permission is recorded:

- do not commit downloaded HTML, ZIP or XLSX files;
- do not upload workbooks or candidate JSONL as public artifacts;
- do not copy full notice prose into the repository;
- keep the source at `candidate` and publish only structural diagnostics;
- retain official URLs and factual field mappings in code and documentation.

## Gates before prototype

- Pass the expanded probe plus inventory workflow on GitHub Actions.
- Parse at least two notices covering both direct-XLSX and ZIP packaging.
- Implement sampling-number grouping, continuation-row handling and Excel date
  conversion with regression fixtures.
- Define correction semantics for repeated or amended sampling numbers.
- Review the domestic-scope record model and prevent mixed overseas statistics.
- Complete a field-by-field candidate review without publicly redistributing the
  candidate artifact while reuse rights remain unclear.
- Record a reuse/attribution decision for normalized facts and short reason text.

Only then should SAMR move from `candidate` to `prototype`. Production
publication requires the full project checklist after that.
