# Data attribution

The project code is licensed under MIT. Regulatory source data and normalized
derivatives retain the source-specific terms below and are not relicensed as
project code.

## Taiwan TFDA border noncompliance

- Data provider: 衛生福利部食品藥物管理署 (Taiwan Food and Drug Administration)
- Dataset: 不符合食品資訊資料集
- Dataset page: <https://data.gov.tw/dataset/6133>
- License: 政府資料開放授權條款-第1版
- License text: <https://data.gov.tw/license>

Attribution used for the 2026 snapshot:

> 資料提供：衛生福利部食品藥物管理署，2026，《不符合食品資訊資料集》（資料提供者未標示獨立版本號）；本專案提供標準化衍生資料。

The release metadata records the retrieval timestamp, record count, source
links, licence link and attribution statement beside each published snapshot.
The source authority does not endorse this project, and the normalized project
categories and hazard tags are not official TFDA classifications.

## EU RASFF Food and Feed Alert Notifications

- Data provider: © European Union; European Commission, DG SANTE
- System: Rapid Alert System for Food and Feed (RASFF)
- Dataset: Food and Feed Alert Notifications
- Dataset page: <https://data.europa.eu/data/datasets/restored_rasff>
- RASFF Window: <https://webgate.ec.europa.eu/rasff-window/screen/search>
- Licence: Creative Commons Attribution 4.0 International (CC BY 4.0)
- Licence text: <https://creativecommons.org/licenses/by/4.0/>
- Commission legal notice: <https://commission.europa.eu/legal-notice_en>

Attribution approved for a future normalized 2026 release:

> Source: © European Union, 1995–2026; European Commission, Directorate-General
> for Health and Food Safety (DG SANTE), Rapid Alert System for Food and Feed
> (RASFF), “Food and Feed Alert Notifications” / RASFF Window. Retrieved
> `{retrieved_at}` from the linked official notification and dataset. Source
> material is licensed under CC BY 4.0. This project selected China-origin
> human-food notifications, normalized fields and dates, added stable IDs,
> lifecycle status and deterministic search labels, and may provide reviewed
> translations; changes were made. The European Commission and RASFF do not
> endorse this project.

The release metadata must preserve the dataset, notification, licence and legal
notice links. It must identify project transformations and must not use EU logos
or imply endorsement. Full review and Chinese companion wording:
[`reviews/RASFF_REUSE_REVIEW.md`](reviews/RASFF_REUSE_REVIEW.md).

## Japan MHLW food recall public information

- Data provider: 厚生労働省 (Ministry of Health, Labour and Welfare, Japan)
- System: 食品衛生申請等システム 食品リコール公開情報
- MHLW information page:
  <https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/kenkou_iryou/shokuhin/kigu/index_00012.html>
- Terms: <https://www.mhlw.go.jp/chosakuken/index.html>
- Licence: 公共データ利用規約（第1.0版） / Public Data License 1.0
- Licence text:
  <https://www.digital.go.jp/resources/open_data/public_data_license_v1.0>

Approved wording for MHLW-linked normalized records:

> 出典：厚生労働省「食品衛生申請等システム 食品リコール公開情報」
> （当該公開情報URL）、公共データ利用規約（第1.0版）（規約URL）、
> `{retrieved_at}`利用。本プロジェクトが中国産食品を選別し、項目・日付を
> 標準化し、検索用分類を付与して加工・作成したものであり、厚生労働省又は
> 日本国政府が作成・承認したものではありません。

Initial publication is limited to records with a verified linked MHLW
`RCL...` detail. CAA recall pages are used for discovery and cross-checking;
CAA-only expressive content is not approved for publication by this review.
See [`reviews/JAPAN_REUSE_REVIEW.md`](reviews/JAPAN_REUSE_REVIEW.md).
