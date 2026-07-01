# EU RASFF reuse and attribution review

## Review status

`passed_for_normalized_facts_with_attribution` — normalized RASFF facts may be
published under the source-specific CC BY 4.0 conditions described below. This
review does not cover EU logos, trademarks, third-party works, personal data,
full page copies, screenshots or attached documents.

## Official evidence

- Dataset: Food and Feed Alert Notifications
  <https://data.europa.eu/data/datasets/restored_rasff>
- RASFF Window:
  <https://webgate.ec.europa.eu/rasff-window/screen/search>
- European Commission legal notice:
  <https://commission.europa.eu/legal-notice_en>
- CC BY 4.0 legal code:
  <https://creativecommons.org/licenses/by/4.0/legalcode.en>
- CC BY 4.0 canonical licence URL:
  <https://creativecommons.org/licenses/by/4.0/>

The data.europa metadata identifies the current RASFF Window/API distribution
as CC BY 4.0. The Commission legal notice says EU-owned website content is CC BY
4.0 unless a specific notice says otherwise, and permits reuse when appropriate
credit is given and changes are indicated. It also excludes logos, names and
other industrial-property rights and warns that third-party rights may require
separate clearance.

CC BY 4.0 section 3 requires, when supplied and reasonably practicable,
identification of the creator/attribution party, copyright and licence notices,
the disclaimer notice, a link to the material, a licence link, and an indication
of modifications. It prohibits implying endorsement. Section 4 expressly covers
extraction and reuse of database contents subject to the attribution conditions.

## Approved attribution statement

For a 2026 English release:

> Source: © European Union, 1995–2026; European Commission, Directorate-General
> for Health and Food Safety (DG SANTE), Rapid Alert System for Food and Feed
> (RASFF), “Food and Feed Alert Notifications” / RASFF Window. Retrieved
> `{retrieved_at}` from the linked official notification and dataset. Source
> material is licensed under CC BY 4.0. This project selected China-origin
> human-food notifications, normalized fields and dates, added stable IDs,
> lifecycle status and deterministic search labels, and may provide reviewed
> translations; changes were made. The European Commission and RASFF do not
> endorse this project.

Chinese companion wording:

> 数据来源：© European Union, 1995–2026；欧盟委员会卫生与食品安全总司
> （DG SANTE）快速预警系统（RASFF）“Food and Feed Alert Notifications” /
> RASFF Window，抓取时间 `{retrieved_at}`，原始通知与数据集链接见记录。
> 来源材料采用 CC BY 4.0；本项目筛选中国来源的人类食品通知，进行字段与日期
> 标准化，添加稳定 ID、生命周期状态和确定性检索标签，并可能提供经审核的翻译；
> 内容已被修改。欧盟委员会与 RASFF 不为本项目背书。

Each release metadata file must also contain direct links to:

- the dataset and RASFF Window;
- <https://creativecommons.org/licenses/by/4.0/>;
- <https://commission.europa.eu/legal-notice_en>;
- the project transformation/method documentation.

Each record retains its direct official notification URL. Attribution may be
provided in release metadata rather than repeated verbatim in every JSONL row,
provided the metadata is distributed alongside the data and clearly linked.

## Reuse boundaries

Allowed by this project decision:

- normalized factual fields and short official reason/hazard text;
- official identifiers, dates, categories, statuses, measures and source URLs;
- project-created classifications, stable IDs and lifecycle labels, clearly
  identified as modifications;
- redistribution of the normalized release with CC BY 4.0 source attribution.

Not approved by this review:

- copying or redistributing RASFF HTML, JavaScript, screenshots or full pages;
- downloading or publishing attachments;
- using EU, Commission or RASFF logos, marks or names as project branding;
- implying official status, sponsorship or endorsement;
- stripping source links, licence/change notices or disclaimer references;
- applying technical/legal restrictions to the source material that conflict
  with CC BY 4.0.

## Disclaimer handling

Release metadata and the public site must state that RASFF information is
received from official contact points, may be corrected or withdrawn, and is not
professional advice. Origin-country inclusion does not mean the identified
hazard originated in that country. The project's status audit and direct source
links help users verify the current official record.

## Production requirement

The future RASFF publishing code must generate source-specific release metadata
containing the approved wording and links. RASFF cannot become `implemented`
until that metadata is produced and validated in the same fail-closed workflow
as the JSONL release.
