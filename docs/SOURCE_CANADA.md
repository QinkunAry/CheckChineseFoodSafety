# Canada recalls source assessment

## Decision

The Government of Canada Recalls and Safety Alerts dataset is a strong candidate
source for food recalls. It has an official daily-updated open dataset in JSON
and CSV, a Food RSS feed, stable detail pages, and clear open-data licensing.

The source is **not yet a prototype** for this project because the open dataset
and inspected detail page do not expose a stable explicit country-of-origin
field. The project must not infer Chinese origin from brand, product wording,
language, importer, cuisine, or company names.

## Official endpoints

- Recalls and Safety Alerts portal:
  <https://recalls-rappels.canada.ca/en>
- Food-filtered search:
  <https://recalls-rappels.canada.ca/en/search/site?f%5B0%5D=cat%3A144>
- Food RSS feed:
  <https://recalls-rappels.canada.ca/en/feed/cfia-alerts-recalls>
- Open Canada dataset page:
  <https://open.canada.ca/data/en/dataset/d38de914-c94c-429b-8ab1-8776c31643e3>
- Open Canada package metadata API:
  <https://open.canada.ca/data/api/action/package_show?id=d38de914-c94c-429b-8ab1-8776c31643e3>
- English JSON feed:
  <https://recalls-rappels.canada.ca/sites/default/files/opendata-donneesouvertes/HCRSAMOpenData.json>
- English CSV feed:
  <https://recalls-rappels.canada.ca/sites/default/files/opendata-donneesouvertes/HCRSAMOpenData.csv>

## Availability findings (2026-06-24)

- The Recalls and Safety Alerts portal states that recall and alert data is
  available in CSV and JSON formats and updated daily.
- The portal reported 19,247 active and 14,440 archived records across all
  recall categories on 2026-06-24.
- The food-filtered search reported 1,203 Food records on 2026-06-24.
- The Open Canada package metadata API returned successfully for dataset
  `d38de914-c94c-429b-8ab1-8776c31643e3`.
- The dataset title is `Recalls and Safety Alerts`.
- The dataset licence is `Open Government Licence - Canada`.
- The dataset notes describe the recalls site as the official Government of
  Canada centralized website for recalls and safety alerts related to food,
  consumer products, health products, medical devices, cannabis, and vehicles.
- The dataset notes state that the open dataset is updated daily and provides
  content for use on third-party platforms or applications.
- The English JSON feed is available at the official `recalls-rappels.canada.ca`
  URL listed above.
- The Food RSS feed returned current CFIA food recall items.

## Open data fields observed

The English JSON feed uses a flat record structure with fields including:

- `NID`
- `Title`
- `URL`
- `Organization`
- `Product`
- `Issue`
- `What you should do`
- `Category`
- `Recall class`
- `Last updated`
- `Archived`

Food records can be identified by `Organization == "CFIA"` and food categories,
but the observed open-data fields do not include explicit country of origin.

## Detail page fields observed

The inspected CFIA detail page for `NID` 82236 exposed:

- title;
- brand;
- last updated date;
- product;
- issue types;
- distribution regions;
- affected product table;
- long issue text;
- background;
- alert / recall type;
- food category;
- recalling firm;
- published-by authority;
- audience;
- recall class;
- identification number;
- CFIA ID.

The inspected page did not expose a stable country-of-origin field.

## Origin evidence probe

`probe-canada-origin` is a read-only diagnostic command. It reads the official
English JSON feed, filters CFIA food records, then samples:

- the latest CFIA food records; and
- additional CFIA food records whose open-data text mentions `China` or
  `Chinese`.

The command does **not** treat China/Chinese mentions as origin evidence. It
uses those mentions only to find likely pages for manual/automated inspection.
Only explicit phrases such as `Country of origin`, `Product of`, `Imported
from`, `Manufactured in`, or `Made in` count as origin evidence.

Live result on 2026-06-24:

- total open-data records: 33,692;
- CFIA food records: 5,243;
- CFIA food records with China/Chinese mentions in open-data text: 12;
- detail pages sampled: 32;
- pages with any supported origin evidence phrase: 0;
- pages with China origin evidence: 0.

Command used:

```powershell
python -m food_safety_watch probe-canada-origin --limit 20 --china-mention-limit 20 --report reports/canada_origin_probe.json
```

## Evidence and filtering rules

Before normalized records can be generated for this project:

- include only records published by CFIA or otherwise explicitly categorized as
  Food;
- include a China-origin record only when an explicit official field or official
  text states country of origin / imported from / product of China in a
  verifiable way;
- never infer Chinese origin from Chinese-sounding brands, Chinese-language
  product names, cuisine, importer, recalling firm, UPC, or URL slug;
- keep Canada recall records distinct from import refusals and safety alerts;
- preserve the official URL and stable `NID` or recall identification number.

## Reuse review

The Open Canada metadata reports `Open Government Licence - Canada`.

Project decision:

- Canada remains `candidate`;
- future reuse must include attribution to the Government of Canada and the
  relevant publishing organization, such as the Canadian Food Inspection Agency;
- normalized facts and direct source links are likely suitable for publication
  under the licence, but exact attribution wording must be included before
  production release;
- do not publish page images, full HTML mirrors, or non-data assets unless their
  reuse status is separately confirmed.

## Known blockers before prototype

- A stable explicit origin-country extraction method has not been found.
- The open JSON/CSV feed is good for recall discovery, but insufficient for
  China-origin filtering on its own.
- Initial latest-record and China/Chinese-mention detail-page sampling found no
  supported origin evidence phrases.
- A diagnostic probe and unit tests exist, but no Canada smoke/prototype command
  should be added until an origin evidence source is found.

## Prototype gate

Before Canada can move from `candidate` to `prototype`, the project needs:

- either a documented origin evidence source, or a deliberate product decision
  that Canada is useful only for general food recall monitoring outside the
  China-origin dataset;
- if a documented origin source is found, a `smoke-canada` command that reads
  the official JSON feed or Food RSS feed;
- deterministic food-record filtering;
- documented handling for records with no explicit origin evidence;
- at least two official records with explicit China-origin evidence, or a clear
  decision that Canada can only be used for general food recall monitoring and
  not for China-origin publication;
- schema validation for any normalized records;
- tests for official host validation, food filtering, non-China/unknown-origin
  exclusion, missing critical fields, and feed failure reporting.

Canada must satisfy the shared
[`prototype` to `implemented` checklist](PROTOTYPE_TO_IMPLEMENTED_CHECKLIST.md)
before any records are published under `data/processed/`.
