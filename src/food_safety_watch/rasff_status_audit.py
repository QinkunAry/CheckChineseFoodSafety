from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from .rasff_detail import detail_api_url, normalize_detail, parse_detail
from .rasff_probe import SOURCE_ID, JsonFetcher, fetch_public_json


AUDIT_FIELDS = (
    "event_date",
    "origin_country",
    "record_status",
    "product_category",
    "product_name",
    "reasons",
    "hazard_tags",
    "official_notification_classification",
    "official_risk_decision",
    "official_notification_basis",
    "official_notification_status",
    "official_distribution_status",
    "official_last_update",
    "official_hazards",
    "official_measures",
    "official_followup_types",
)


def notification_id_from_source_url(url: str) -> int:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "webgate.ec.europa.eu":
        raise ValueError("RASFF audit source URL must use the official HTTPS host")
    match = re.fullmatch(r"/rasff-window/screen/notification/(\d+)", parsed.path)
    if not match or parsed.query or parsed.fragment:
        raise ValueError("RASFF audit source URL has an unexpected detail path")
    return int(match.group(1))


def _validate_published_record(record: dict[str, Any], index: int) -> tuple[str, int]:
    if record.get("source_id") != SOURCE_ID:
        raise ValueError(f"published record {index} is not from {SOURCE_ID}")
    reference = record.get("source_record_id")
    if not isinstance(reference, str) or not reference:
        raise ValueError(f"published record {index} lacks source_record_id")
    source_url = record.get("source_url")
    if not isinstance(source_url, str):
        raise ValueError(f"published record {index} lacks source_url")
    if record.get("record_status") not in {
        "active",
        "withdrawn",
        "review_required",
    }:
        raise ValueError(f"published record {index} lacks a valid record_status")
    if not isinstance(record.get("official_last_update"), str):
        raise ValueError(f"published record {index} lacks official_last_update")
    return reference, notification_id_from_source_url(source_url)


def audit_rasff_records(
    records: list[dict[str, Any]],
    *,
    fetcher: JsonFetcher = fetch_public_json,
    max_records: int = 100,
) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat()
    if max_records < 1:
        raise ValueError("RASFF status audit max_records must be at least 1")
    if not records:
        return {
            "status": "failed",
            "generated_at": generated_at,
            "source_id": SOURCE_ID,
            "published_record_count": 0,
            "blocking_errors": ["RASFF status audit input is empty"],
        }
    if len(records) > max_records:
        return {
            "status": "failed",
            "generated_at": generated_at,
            "source_id": SOURCE_ID,
            "published_record_count": len(records),
            "maximum_records": max_records,
            "blocking_errors": [
                f"published record count {len(records)} exceeds audit maximum "
                f"{max_records}; use an approved batching plan or raise explicitly"
            ],
        }

    blocking_errors: list[str] = []
    change_samples: list[dict[str, Any]] = []
    changed_record_count = 0
    references: set[str] = set()
    audited_count = 0
    for index, published in enumerate(records):
        try:
            reference, notification_id = _validate_published_record(published, index)
            if reference in references:
                raise ValueError(f"duplicate published RASFF reference: {reference}")
            references.add(reference)
            detail = parse_detail(
                fetcher(detail_api_url(notification_id), None),
                expected_id=notification_id,
                expected_reference=reference,
            )
            current = normalize_detail(
                detail,
                retrieved_at=str(published.get("retrieved_at") or generated_at),
            )
            changed_fields: list[str]
            if current is None:
                changed_fields = ["regulatory_scope"]
                current_status = "out_of_scope"
            else:
                changed_fields = [
                    field
                    for field in AUDIT_FIELDS
                    if published.get(field) != current.get(field)
                ]
                current_status = current["record_status"]
            if changed_fields:
                changed_record_count += 1
                if len(change_samples) < 50:
                    change_samples.append(
                        {
                            "reference": reference,
                            "notification_id": notification_id,
                            "previous_record_status": published["record_status"],
                            "current_record_status": current_status,
                            "previous_last_update": published["official_last_update"],
                            "current_last_update": detail["last_update_raw"],
                            "changed_fields": changed_fields,
                        }
                    )
            audited_count += 1
        except Exception as error:
            blocking_errors.append(
                f"published record {index} audit failed: "
                f"{type(error).__name__}: {error}"
            )

    status = (
        "failed"
        if blocking_errors
        else "action_required"
        if changed_record_count
        else "passed"
    )
    return {
        "status": status,
        "generated_at": generated_at,
        "source_id": SOURCE_ID,
        "published_record_count": len(records),
        "maximum_records": max_records,
        "audited_record_count": audited_count,
        "changed_record_count": changed_record_count,
        "change_samples": change_samples,
        "blocking_errors": blocking_errors,
        "warnings": [
            "action_required means the published snapshot is stale; rebuild it "
            "through the future fail-closed publishing workflow rather than "
            "editing records in place."
        ],
    }
