# EU RASFF source assessment

## Decision

The European Commission Rapid Alert System for Food and Feed (RASFF) is a
high-value candidate source, but it is **not yet a prototype** in this project.

The preferred path is the official data.europa / DG SANTE DataLake dataset and
API metadata, not scraping the RASFF Window Angular application. RASFF should
move to `prototype` only after a live sample payload confirms the endpoint,
authorization model, fields, and rate limits.

## Official endpoints

- European Commission RASFF overview:
  <https://food.ec.europa.eu/food-safety/rasff_en>
- RASFF Window search interface:
  <https://webgate.ec.europa.eu/rasff-window/screen/search>
- RASFF Window public configuration:
  <https://webgate.ec.europa.eu/rasff-window/backend/public/configuration/>
- data.europa dataset page:
  <https://data.europa.eu/data/datasets/restored_rasff~~1?locale=en>
- data.europa dataset metadata API:
  <https://data.europa.eu/api/hub/repo/datasets/restored_rasff>
- DG SANTE developer portal entry:
  <https://developer.datalake.sante.service.ec.europa.eu/api-details#api=c5ad39eb-712e-4cb4-a7f6-764de863ae7e&operation=cc6aab62-bd15-4904-b20d-54551ccb9468>

## Availability findings (2026-06-24)

- The European Commission RASFF page describes RASFF Window as the public
  searchable database for summary notification information. It also states that
  public search is currently limited to notifications from 2020 onward.
- RASFF Window public configuration exposes an `openPortalLink` that points to
  the data.europa dataset `restored_rasff`.
- The data.europa metadata API returns JSON-LD for dataset `restored_rasff`.
- The dataset metadata lists a JSON distribution named `Food and Feed Alert
  Notifications`, modified on 2025-03-07, licensed as
  `CC_BY_4_0`.
- The dataset metadata says the API data corresponds to the public RASFF Window
  information and is currently restricted to notifications from 2020 onward.
- The metadata also lists a pre-2021 XLSX resource for historical public
  information.
- The metadata lists an `APIs User Guide - Download` PDF URL, but on
  2026-06-24 that URL returned:
  `{ "statusCode": 404, "message": "Resource not found" }`.
- The DG SANTE developer portal API list is rendered through a custom widget
  that asks the parent portal for `managementApiUrl`, `apiVersion`, and optional
  token at runtime. Direct HTML fetches do not expose the API catalog.
- Common unauthenticated APIM catalog guesses under `/developer/apis` returned
  404 or 500 on 2026-06-24, so they are not usable as documented endpoints.

## Evidence and filtering rules

RASFF contains both food and feed notifications. This project is consumer food
focused, so the first implementation should:

- include only human-food records unless a deliberate feed scope is approved;
- include a record only when an explicit official origin field identifies China
  or the People's Republic of China;
- never infer origin from cuisine, brand, product wording, exporter, importer,
  or free-text narrative alone;
- preserve direct links to the official dataset or notification where available;
- keep RASFF notification type distinct from FDA import refusals, FSANZ recalls,
  and CFS safety alerts.

## Reuse review

The data.europa metadata identifies the RASFF Window distribution, API user guide
distribution, JSON API distribution, and pre-2021 XLSX resource as
`CC_BY_4_0`.

Project decision:

- RASFF remains `candidate`;
- any future publication must include attribution to the European Commission /
  DG SANTE / RASFF and direct source links;
- before publishing normalized RASFF records, the exact attribution wording,
  endpoint terms, and API usage limits must be confirmed from the developer
  portal or API guide;
- do not commit scraped RASFF Window HTML or JavaScript as project data.

## Known blockers before prototype

- The official API user guide download currently returns 404.
- A live API sample payload has not been retrieved.
- The endpoint's authentication or subscription requirements are not confirmed.
- The developer portal appears to provide API catalog details through runtime
  portal secrets rather than static HTML.
- Field names for product category, country of origin, notification type, date,
  risk, and reference ID are not yet mapped to `record.schema.json`.
- The food/feed exclusion rule must be validated against real API fields.

## Prototype gate

Before RASFF can move from `candidate` to `prototype`, the project needs:

- a documented official API or export URL that returns live records;
- a minimal `smoke-rasff` command using a tiny date range or fixed reference
  sample;
- at least two explicit China-origin human-food records and one non-China record
  verified against live official data;
- schema validation for normalized records;
- tests for URL/host validation, China-origin filtering, non-China exclusion,
  missing critical fields, and API failure reporting.

RASFF must satisfy the shared
[`prototype` to `implemented` checklist](PROTOTYPE_TO_IMPLEMENTED_CHECKLIST.md)
before any records are published under `data/processed/`.
