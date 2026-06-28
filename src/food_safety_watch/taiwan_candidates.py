from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .classification import classify_reasons
from .models import SafetyRecord, stable_id
from .quality import build_quality_report
from .taiwan_inventory import load_record_state, new_records
from .taiwan_probe import (
    SEARCH_URL,
    SOURCE_ID,
    fetch_dataset,
    is_china_origin,
    is_human_food_candidate,
    normalize_date,
    parse_dataset,
    stable_record_id,
)


AUTHORITY = "Taiwan Food and Drug Administration"


def product_category(record: dict[str, str]) -> str:
    tariff_code = record.get("貨品分類號列", "").strip()
    if tariff_code.startswith(("2836.30", "3203.00", "3301.90", "3802.90")):
        return "food_additives_and_processing_aids"
    if tariff_code.startswith("1905.90.10"):
        return "food_capsules"
    match = re.match(r"\s*(\d{2})", tariff_code)
    chapter = int(match.group(1)) if match else 0
    categories = {
        2: "meat_and_poultry",
        3: "seafood",
        4: "dairy_and_eggs",
        7: "vegetables",
        8: "fruit",
        9: "coffee_tea_and_spices",
        10: "grains",
        11: "milled_grain_products",
        12: "seeds_and_herbs",
        13: "plant_extracts",
        15: "oils_and_fats",
        16: "prepared_meat_and_seafood",
        17: "sugar_and_confectionery",
        18: "cocoa_and_chocolate",
        19: "bakery_and_cereal_products",
        20: "prepared_fruit_and_vegetables",
        21: "prepared_foods",
        22: "beverages",
    }
    return categories.get(chapter, "other_food")


def hazard_tags(reasons: list[str]) -> list[str]:
    text = " ".join(reasons)
    rules = {
        "microbiological": (
            "微生物", "沙門氏菌", "李斯特菌", "大腸桿菌", "大腸菌", "腸桿菌",
            "生菌數", "黴菌", "酵母菌", "金黃色葡萄球菌", "諾羅病毒",
        ),
        "chemical": (
            "農藥", "動物用藥", "重金屬", "防腐劑", "甜味劑", "漂白劑",
            "著色劑", "二氧化硫", "塑化劑", "三聚氰胺", "真菌毒素",
            "污染物質", "毒素", "抗氧化劑", "化學",
            "戴奧辛", "多氯聯苯", "環氧乙烷", "磷酸鹽", "氯化物", "污染", "咖啡因",
        ),
        "allergen": ("過敏原", "致敏"),
        "labeling": ("標示", "標籤"),
        "adulteration": ("異物", "摻偽", "混充"),
    }
    tags = [tag for tag, keywords in rules.items() if any(keyword in text for keyword in keywords)]
    return tags or classify_reasons(reasons)


def _deduplicate(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        normalized = re.sub(r"\s+", " ", value).strip()
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def parse_candidate_record(
    record: dict[str, str],
    *,
    retrieved_at: str,
) -> SafetyRecord | None:
    if not is_china_origin(record) or not is_human_food_candidate(record):
        return None
    reasons = _deduplicate([
        record.get("原因", ""),
        record.get("不合格原因暨檢出量詳細說明", ""),
    ])
    if not record.get("主旨", "").strip():
        raise ValueError("Taiwan TFDA record does not contain a product name")
    if not reasons:
        raise ValueError("Taiwan TFDA record does not contain a reason")
    source_record_id = stable_record_id(record)
    return SafetyRecord(
        id=stable_id(SOURCE_ID, source_record_id),
        source_id=SOURCE_ID,
        source_record_id=source_record_id,
        authority=AUTHORITY,
        authority_region="TW",
        action_type="inspection_failure",
        event_date=normalize_date(record["發布日期"]),
        origin_country="CN",
        producer_name=record.get("製造廠或出口商名稱", "").strip(),
        producer_location="",
        product_code=record.get("貨品分類號列", "").strip(),
        product_category=product_category(record),
        product_name=record["主旨"].strip(),
        reasons=reasons,
        hazard_tags=hazard_tags(reasons),
        source_url=SEARCH_URL,
        retrieved_at=retrieved_at,
    )


def build_candidate_report(
    *,
    records: list[dict[str, str]],
    schema: dict[str, Any],
    retrieved_at: str | None = None,
    baseline_count: int = 0,
    current_count: int | None = None,
    scope: str = "new_since_baseline",
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    generated_at = retrieved_at or datetime.now(timezone.utc).isoformat()
    candidates: list[dict[str, Any]] = []
    parse_error_samples: list[dict[str, str]] = []
    parse_error_count = 0
    blocking_errors: list[str] = []
    china_count = 0
    china_non_food_count = 0
    for record in records:
        if is_china_origin(record):
            china_count += 1
            if not is_human_food_candidate(record):
                china_non_food_count += 1
        try:
            candidate = parse_candidate_record(record, retrieved_at=generated_at)
            if candidate is not None:
                candidates.append(candidate.to_dict())
        except Exception as error:
            parse_error_count += 1
            detail = f"{type(error).__name__}: {error}"
            blocking_errors.append(
                f"record parse failed: {stable_record_id(record)}: {detail}"
            )
            if len(parse_error_samples) < 20:
                parse_error_samples.append({
                    "source_record_id": stable_record_id(record),
                    "product_name": record.get("主旨", ""),
                    "error": detail,
                })

    quality = build_quality_report(candidates, schema, source_id=SOURCE_ID, min_records=0)
    blocking_errors.extend(str(error) for error in quality["blocking_errors"])
    return (
        {
            "status": "failed" if blocking_errors else "passed",
            "generated_at": generated_at,
            "source_id": SOURCE_ID,
            "scope": scope,
            "baseline_count": baseline_count,
            "current_count": current_count if current_count is not None else len(records),
            "new_record_count": len(records),
            "new_china_record_count": china_count,
            "china_human_food_candidate_count": len(candidates),
            "excluded_non_china_count": len(records) - china_count,
            "excluded_china_non_food_count": china_non_food_count,
            "candidate_samples": candidates[:10],
            "parse_error_count": parse_error_count,
            "parse_error_samples": parse_error_samples,
            "schema_error_count": quality["schema_error_count"],
            "schema_error_samples": quality["schema_error_samples"],
            "duplicate_id_count": quality["duplicate_id_count"],
            "event_date_min": quality["event_date_min"],
            "event_date_max": quality["event_date_max"],
            "product_categories": quality["product_categories"],
            "hazard_tags": quality["hazard_tags"],
            "blocking_errors": blocking_errors,
        },
        candidates,
    )


def candidate_taiwan_tfda(
    *,
    state_path: Path,
    schema: dict[str, Any],
    payload: bytes | str | None = None,
    include_current: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    current = parse_dataset(payload if payload is not None else fetch_dataset())
    previous_ids = load_record_state(state_path)
    selected = current if include_current else new_records(current, previous_ids)
    return build_candidate_report(
        records=selected,
        schema=schema,
        baseline_count=len(previous_ids),
        current_count=len(current),
        scope="all_current" if include_current else "new_since_baseline",
    )
