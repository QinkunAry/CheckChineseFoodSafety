from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .quality import build_quality_report
from .rasff_detail import (
    detail_api_url,
    is_china_food_detail,
    normalize_detail,
    parse_detail,
)
from .rasff_probe import SOURCE_ID, JsonFetcher, fetch_public_json


def _sample(detail: dict[str, Any]) -> dict[str, Any]:
    return {
        "notification_id": detail["notification_id"],
        "reference": detail["reference"],
        "product_name": detail["product_name"],
        "product_category": detail["product_category"],
        "product_type": detail["product_type"],
        "classification": detail["classification"],
        "risk_decision": detail["risk_decision"],
        "notification_status": detail["notification_status"],
        "origin_codes": detail["origin_codes"],
        "hazard_count": len(detail["hazards"]),
        "hazards": detail["hazards"],
    }


def build_detail_smoke_report(
    *,
    china_ids: list[int],
    control_ids: list[int],
    schema: dict[str, Any],
    fetcher: JsonFetcher = fetch_public_json,
) -> dict[str, Any]:
    if len(china_ids) < 2 or not control_ids:
        raise ValueError("RASFF detail smoke requires two China IDs and one control ID")
    generated_at = datetime.now(timezone.utc).isoformat()
    blocking_errors: list[str] = []
    china_details: list[dict[str, Any]] = []
    control_details: list[dict[str, Any]] = []
    page_results: list[dict[str, Any]] = []

    for expected_scope, notification_ids in (
        ("china", china_ids),
        ("control", control_ids),
    ):
        for notification_id in notification_ids:
            url = detail_api_url(notification_id)
            try:
                detail = parse_detail(
                    fetcher(url, None), expected_id=notification_id
                )
                is_china = is_china_food_detail(detail)
                if expected_scope == "china" and not is_china:
                    raise ValueError("expected China-origin human-food detail")
                if expected_scope == "control" and is_china:
                    raise ValueError("non-China control normalized as China food")
                (china_details if expected_scope == "china" else control_details).append(
                    detail
                )
                page_results.append(
                    {
                        "notification_id": notification_id,
                        "reference": detail["reference"],
                        "expected_scope": expected_scope,
                        "status": "passed",
                    }
                )
            except Exception as error:
                detail_text = f"{type(error).__name__}: {error}"
                blocking_errors.append(
                    f"detail {notification_id} fetch/parse failed: {detail_text}"
                )
                page_results.append(
                    {
                        "notification_id": notification_id,
                        "expected_scope": expected_scope,
                        "status": "failed",
                        "error": detail_text,
                    }
                )

    normalized = [
        record
        for record in (
            normalize_detail(detail, retrieved_at=generated_at)
            for detail in china_details
        )
        if record is not None
    ]
    control_emitted_count = sum(
        normalize_detail(detail, retrieved_at=generated_at) is not None
        for detail in control_details
    )
    if control_emitted_count:
        blocking_errors.append(
            f"detail controls emitted {control_emitted_count} China records"
        )
    quality = build_quality_report(
        normalized,
        schema,
        source_id=SOURCE_ID,
        min_records=len(china_ids),
    )
    blocking_errors.extend(str(error) for error in quality["blocking_errors"])
    references = [detail["reference"] for detail in china_details + control_details]
    if len(references) != len(set(references)):
        blocking_errors.append("RASFF detail smoke returned duplicate references")

    return {
        "status": "failed" if blocking_errors else "passed",
        "generated_at": generated_at,
        "source_id": SOURCE_ID,
        "china_detail_count": len(china_details),
        "control_detail_count": len(control_details),
        "normalized_china_count": len(normalized),
        "control_emitted_count": control_emitted_count,
        "withdrawn_china_count": sum(
            detail["notification_status"] == "ec_withdrawn"
            for detail in china_details
        ),
        "hazard_detail_count": sum(len(detail["hazards"]) for detail in china_details),
        "schema_error_count": quality["schema_error_count"],
        "schema_error_samples": quality["schema_error_samples"],
        "duplicate_id_count": quality["duplicate_id_count"],
        "page_results": page_results,
        "china_samples": [_sample(detail) for detail in china_details],
        "control_samples": [_sample(detail) for detail in control_details],
        "blocking_errors": blocking_errors,
    }
