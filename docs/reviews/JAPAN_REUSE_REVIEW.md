# Japan CAA / MHLW reuse review

Status: `approved_for_mhlw_linked_normalized_records_only`  
Reviewed: 2026-07-02

## Official evidence

- MHLW terms: <https://www.mhlw.go.jp/chosakuken/index.html>
- CAA terms: <https://www.caa.go.jp/terms_of_use/>
- Public Data License 1.0: <https://www.digital.go.jp/resources/open_data/public_data_license_v1.0>
- CAA recall-site about page: <https://www.recall.caa.go.jp/about/index.php>

The MHLW terms say that MHLW website content is available under PDL 1.0 unless
otherwise stated. They require the source and page URL, and require a separate
statement when content is edited or processed. Processed information must not
be presented as if MHLW or the national government created it. Logos, symbols
and content under separately stated terms are excluded.

The main CAA website publishes equivalent PDL 1.0 attribution and processing
requirements. However, the inspected `recall.caa.go.jp` about page displays a
CAA copyright notice but does not itself expose an explicit PDL 1.0 statement.
This project therefore does not assume that the main-site terms automatically
authorize copying expressive content from the recall subdomain.

## Approved initial boundary

- CAA food-list and detail URLs may be used for discovery, identifiers,
  cross-checking and links.
- Initial published content must come from an official linked MHLW public
  recall detail whose `RCL...` identifier is verified.
- The normalized record uses the MHLW recall ID as `source_record_id`, the MHLW
  detail as `source_url`, and MHLW as the authority.
- Do not publish CAA-only reason/product prose until the recall subdomain reuse
  basis is separately documented.
- Do not copy HTML, images, logos, attachments or third-party material.
- Project categories, hazard labels, translations and field normalization must
  be identified as project processing, not official classifications.

## Approved attribution

Japanese display wording:

> 出典：厚生労働省「食品衛生申請等システム 食品リコール公開情報」
> （当該公開情報URL）、公共データ利用規約（第1.0版）（規約URL）、
> `{retrieved_at}`利用。本プロジェクトが中国産食品を選別し、項目・日付を
> 標準化し、検索用分類を付与して加工・作成したものであり、厚生労働省又は
> 日本国政府が作成・承認したものではありません。

English companion wording:

> Source: Ministry of Health, Labour and Welfare, Japan, Food Recall Public
> Information in the Food Sanitation Application System (linked record URL),
> used `{retrieved_at}` under Public Data License 1.0 (linked licence). This
> project selected China-origin food recalls, normalized fields and dates, and
> added search classifications. The processed dataset was not created or
> endorsed by MHLW or the Government of Japan.

## Remaining gate

The two fixed China-origin samples must produce a non-empty MHLW-backed
candidate batch on GitHub Runner. A maintainer must inspect mixed-origin scope,
product wording, event date and recall reason before any production release.
