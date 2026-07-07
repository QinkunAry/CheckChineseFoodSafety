from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .classification import classify_reasons
from .japan_inventory import (
    PageFetcher,
    collect_caa_food_items,
    fetch_caa_food_page,
    load_url_state,
)
from .japan_probe import (
    CAA_FOOD_URL,
    CaaListItem,
    Fetcher,
    SOURCE_ID,
    fetch_official,
    inspect_caa_detail,
    inspect_mhlw_detail,
)
from .japan_smoke import caa_rcl_from_detail_url, mhlw_detail_url
from .models import SafetyRecord, stable_id
from .quality import build_quality_report


CAA_AUTHORITY = "Consumer Affairs Agency, Japan"
MHLW_AUTHORITY = "Ministry of Health, Labour and Welfare, Japan"


def new_recall_items(
    current_items: list[CaaListItem],
    previous_urls: list[str],
) -> list[CaaListItem]:
    previous = set(previous_urls)
    return sorted(
        (item for item in current_items if item.url not in previous),
        key=lambda item: item.url,
    )


def select_candidate_items(
    *,
    current_items: list[CaaListItem],
    previous_urls: list[str],
    review_urls: list[str] | None = None,
) -> tuple[list[CaaListItem], list[str], str]:
    requested: list[str] = []
    for raw in review_urls or []:
        value = raw.strip()
        caa_rcl_from_detail_url(value)
        if value not in requested:
            requested.append(value)
    if not requested:
        return new_recall_items(current_items, previous_urls), [], "new_since_baseline"

    current_by_url = {item.url: item for item in current_items}
    missing = [url for url in requested if url not in current_by_url]
    if missing:
        raise ValueError(
            "requested Japan CAA review URLs are not in the current food inventory: "
            + ", ".join(missing)
        )
    return [current_by_url[url] for url in requested], requested, "explicit_review"


def _normalize_date(*values: str | None) -> str:
    patterns = ("%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日")
    for raw in values:
        value = (raw or "").strip()
        for pattern in patterns:
            try:
                return datetime.strptime(value, pattern).date().isoformat()
            except ValueError:
                continue
    raise ValueError("Japan recall does not contain a supported event date")


def _product_category(value: str) -> str:
    rules = {
        "seafood": ("魚", "うなぎ", "鰻", "えび", "海老", "かに", "蟹", "貝", "水産"),
        "meat_and_poultry": ("肉", "鶏", "豚", "牛", "鴨", "ソーセージ", "ハム"),
        "pasta_and_noodles": ("麺", "めん", "パスタ", "ビーフン"),
        "vegetables": ("野菜", "きのこ", "茸", "とんぶり"),
        "fruit": ("果物", "フルーツ", "梅", "桃", "梨", "ぶどう", "葡萄"),
        "snacks": ("菓子", "クッキー", "ビスケット", "せんべい", "スナック"),
        "candy": ("飴", "キャンディ", "グミ", "チョコ"),
        "prepared_meals_and_sauces": ("惣菜", "弁当", "ソース", "たれ", "餃子"),
        "spices_and_salt": ("香辛料", "調味料", "塩"),
        "coffee_and_tea": ("茶", "コーヒー"),
    }
    for category, keywords in rules.items():
        if any(keyword in value for keyword in keywords):
            return category
    return "other_food"


def _hazard_tags(reasons: list[str]) -> list[str]:
    text = " ".join(reasons)
    rules = {
        "microbiological": (
            "サルモネラ",
            "リステリア",
            "大腸菌",
            "細菌",
            "芽胞菌",
            "クロストリジウム",
            "カビ",
        ),
        "chemical": ("農薬", "化学", "メラミン", "鉛", "カドミウム", "水銀"),
        "allergen": ("アレルゲン", "アレルギー"),
        "labeling": ("表示", "ラベル", "期限", "賞味", "消費期限"),
        "adulteration": ("異物", "混入", "偽装"),
    }
    tags = [
        tag
        for tag, keywords in rules.items()
        if any(keyword in text for keyword in keywords)
    ]
    if tags:
        return tags
    return classify_reasons(reasons)


def _deduplicate(values: list[str | None]) -> list[str]:
    result: list[str] = []
    for raw in values:
        value = re.sub(r"\s+", " ", raw or "").strip()
        if value and value not in result:
            result.append(value)
    return result


def normalize_mhlw_detail(
    *,
    detail: dict[str, Any],
    retrieved_at: str,
    expected_reference: str | None = None,
) -> SafetyRecord | None:
    reference = str(detail.get("rcl_no") or "").strip()
    if not reference:
        raise ValueError("MHLW detail does not contain its recall identifier")
    if expected_reference and reference != expected_reference:
        raise ValueError(f"MHLW recall ID mismatch: {reference} != {expected_reference}")
    if not detail.get("china_origin_evidence"):
        return None
    product_name = str(detail.get("product") or "").strip()
    if not product_name:
        raise ValueError("MHLW detail does not contain a product name")
    reasons = _deduplicate([detail.get("reason_type"), detail.get("reason")])
    if not reasons:
        raise ValueError("MHLW detail does not contain a recall reason")
    return SafetyRecord(
        id=stable_id(SOURCE_ID, reference),
        source_id=SOURCE_ID,
        source_record_id=reference,
        authority=MHLW_AUTHORITY,
        authority_region="JP",
        action_type="recall",
        event_date=_normalize_date(detail.get("event_date"), detail.get("release_date")),
        origin_country="CN",
        producer_name="",
        producer_location="",
        product_code="",
        product_category=_product_category(product_name),
        product_name=product_name,
        reasons=reasons,
        hazard_tags=_hazard_tags(reasons),
        source_url=mhlw_detail_url(reference),
        retrieved_at=retrieved_at,
    )


def parse_candidate_item(
    *,
    item: CaaListItem,
    caa_detail: dict[str, Any],
    mhlw_detail: dict[str, Any] | None,
    retrieved_at: str,
) -> SafetyRecord | None:
    if mhlw_detail is not None:
        return normalize_mhlw_detail(
            detail=mhlw_detail,
            retrieved_at=retrieved_at,
            expected_reference=str(mhlw_detail.get("rcl_no") or ""),
        )
    if not caa_detail.get("china_origin_evidence"):
        return None

    event_date = _normalize_date(
        caa_detail.get("event_date"),
        item.start_date,
        item.post_date,
    )
    product_name = (
        caa_detail.get("product")
        or caa_detail.get("title")
        or item.title
    )
    reasons = _deduplicate([caa_detail.get("reason_type"), caa_detail.get("reason")])
    if not product_name:
        raise ValueError("Japan recall does not contain a product name")
    if not reasons:
        raise ValueError("Japan recall does not contain a recall reason")

    source_record_id = caa_rcl_from_detail_url(item.url)
    return SafetyRecord(
        id=stable_id(SOURCE_ID, source_record_id),
        source_id=SOURCE_ID,
        source_record_id=source_record_id,
        authority=CAA_AUTHORITY,
        authority_region="JP",
        action_type="recall",
        event_date=event_date,
        origin_country="CN",
        producer_name="",
        producer_location="",
        product_code="",
        product_category=_product_category(product_name),
        product_name=product_name,
        reasons=reasons,
        hazard_tags=_hazard_tags(reasons),
        source_url=item.url,
        retrieved_at=retrieved_at,
    )


def build_candidate_report(
    *,
    items: list[CaaListItem],
    schema: dict[str, Any],
    fetcher: Fetcher = fetch_official,
    retrieved_at: str | None = None,
    baseline_count: int = 0,
    current_count: int | None = None,
    inventory_warnings: list[str] | None = None,
    scope: str = "new_since_baseline",
    requested_urls: list[str] | None = None,
    min_china_records: int = 0,
    min_mhlw_records: int = 0,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if min_china_records < 0 or min_mhlw_records < 0:
        raise ValueError("Japan candidate minimum counts must not be negative")
    generated_at = retrieved_at or datetime.now(timezone.utc).isoformat()
    page_results: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    blocking_errors: list[str] = []

    for item in items:
        result: dict[str, Any] = {
            "url": item.url,
            "list_title": item.title,
            "list_post_date": item.post_date,
            "list_start_date": item.start_date,
        }
        try:
            caa_detail = inspect_caa_detail(fetcher(item.url))
            result["caa_china_origin_evidence"] = bool(
                caa_detail.get("china_origin_evidence")
            )
            result["caa_product"] = caa_detail.get("product")
            result["caa_reason_excerpt"] = (
                caa_detail.get("reason") or caa_detail.get("summary") or ""
            )[:300]

            mhlw: dict[str, Any] | None = None
            mhlw_reference = caa_detail.get("mhlw_reference_id")
            if mhlw_reference:
                result["mhlw_reference_id"] = mhlw_reference
                result["mhlw_url"] = mhlw_detail_url(mhlw_reference)
                mhlw = inspect_mhlw_detail(fetcher(result["mhlw_url"]))
                if mhlw.get("rcl_no") and mhlw["rcl_no"] != mhlw_reference:
                    raise ValueError(
                        f"MHLW recall ID mismatch: {mhlw['rcl_no']} != {mhlw_reference}"
                    )
                result["mhlw_china_origin_evidence"] = bool(
                    mhlw.get("china_origin_evidence")
                )
                result["mhlw_reason_excerpt"] = (mhlw.get("reason") or "")[:300]

            record = parse_candidate_item(
                item=item,
                caa_detail=caa_detail,
                mhlw_detail=mhlw,
                retrieved_at=generated_at,
            )
            if record is None:
                result["status"] = "parsed_non_china"
            else:
                normalized = record.to_dict()
                records.append(normalized)
                result.update({
                    "status": "parsed_china",
                    "record_id": normalized["id"],
                    "event_date": normalized["event_date"],
                })
        except Exception as error:
            result["status"] = "error"
            result["error"] = f"{type(error).__name__}: {error}"
            blocking_errors.append(f"page parse failed: {item.url}: {result['error']}")
        page_results.append(result)

    quality = build_quality_report(
        records,
        schema,
        source_id=SOURCE_ID,
        min_records=0,
    )
    blocking_errors.extend(str(error) for error in quality["blocking_errors"])
    mhlw_record_count = sum(
        record.get("authority") == MHLW_AUTHORITY for record in records
    )
    if len(records) < min_china_records:
        blocking_errors.append(
            f"China record count {len(records)} below minimum {min_china_records}"
        )
    if mhlw_record_count < min_mhlw_records:
        blocking_errors.append(
            f"MHLW-backed record count {mhlw_record_count} below minimum {min_mhlw_records}"
        )

    return (
        {
            "status": "failed" if blocking_errors else "passed",
            "generated_at": generated_at,
            "source_id": SOURCE_ID,
            "scope": scope,
            "requested_urls": requested_urls or [],
            "list_url": CAA_FOOD_URL,
            "baseline_count": baseline_count,
            "current_count": current_count if current_count is not None else len(items),
            "candidate_url_count": len(items),
            "tested_page_count": len(page_results),
            "china_record_count": len(records),
            "mhlw_backed_record_count": mhlw_record_count,
            "minimum_china_records": min_china_records,
            "minimum_mhlw_records": min_mhlw_records,
            "inventory_warnings": inventory_warnings or [],
            "page_results": page_results,
            "schema_error_count": quality["schema_error_count"],
            "schema_error_samples": quality["schema_error_samples"],
            "blocking_errors": blocking_errors,
        },
        records,
    )


def candidate_japan_caa(
    *,
    state_path: Path,
    schema: dict[str, Any],
    fetcher: Fetcher = fetch_official,
    page_fetcher: PageFetcher = fetch_caa_food_page,
    review_urls: list[str] | None = None,
    min_china_records: int = 0,
    min_mhlw_records: int = 0,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    current_items, diagnostics = collect_caa_food_items(page_fetcher=page_fetcher)
    previous_urls = load_url_state(state_path)
    items, requested, scope = select_candidate_items(
        current_items=current_items,
        previous_urls=previous_urls,
        review_urls=review_urls,
    )
    return build_candidate_report(
        items=items,
        schema=schema,
        fetcher=fetcher,
        baseline_count=len(previous_urls),
        current_count=len(current_items),
        inventory_warnings=diagnostics.get("warnings", []),
        scope=scope,
        requested_urls=requested,
        min_china_records=min_china_records,
        min_mhlw_records=min_mhlw_records,
    )
