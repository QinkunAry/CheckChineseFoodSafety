from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .japan_candidates import MHLW_AUTHORITY, normalize_mhlw_detail
from .japan_probe import Fetcher, SOURCE_ID, fetch_official, inspect_mhlw_detail
from .japan_update import mhlw_reference_from_url


AUDIT_FIELDS = (
    "event_date",
    "origin_country",
    "product_category",
    "product_name",
    "reasons",
    "hazard_tags",
    "authority",
    "source_url",
)


def audit_japan_records(
    records: list[dict[str, Any]],
    *,
    fetcher: Fetcher = fetch_official,
    max_records: int = 100,
) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat()
    blocking_errors: list[str] = []
    changes: list[dict[str, Any]] = []
    page_results: list[dict[str, Any]] = []
    if max_records < 1:
        raise ValueError("Japan audit max_records must be at least 1")
    if len(records) > max_records:
        blocking_errors.append(
            f"published record count {len(records)} exceeds audit maximum {max_records}"
        )

    references = [record.get("source_record_id") for record in records]
    duplicates = sorted(
        {value for value in references if value and references.count(value) > 1}
    )
    if duplicates:
        blocking_errors.append(f"duplicate published MHLW references: {duplicates}")

    if not blocking_errors:
        for record in records:
            reference = record.get("source_record_id")
            source_url = record.get("source_url")
            result: dict[str, Any] = {
                "reference": reference,
                "source_url": source_url,
            }
            try:
                if record.get("source_id") != SOURCE_ID:
                    raise ValueError(f"source_id must be {SOURCE_ID}")
                if record.get("authority") != MHLW_AUTHORITY:
                    raise ValueError("published Japan record must use MHLW authority")
                if mhlw_reference_from_url(source_url) != reference:
                    raise ValueError("published MHLW source URL/reference mismatch")
                detail = inspect_mhlw_detail(fetcher(str(source_url)))
                if detail.get("rcl_no") != reference:
                    raise ValueError(
                        f"official MHLW recall ID mismatch: {detail.get('rcl_no')} != {reference}"
                    )
                current = normalize_mhlw_detail(
                    detail=detail,
                    retrieved_at=str(record.get("retrieved_at") or generated_at),
                    expected_reference=str(reference),
                )
                if current is None:
                    field_changes = [{
                        "field": "origin_country",
                        "previous": record.get("origin_country"),
                        "current": None,
                    }]
                else:
                    normalized = current.to_dict()
                    field_changes = [
                        {
                            "field": field,
                            "previous": record.get(field),
                            "current": normalized.get(field),
                        }
                        for field in AUDIT_FIELDS
                        if record.get(field) != normalized.get(field)
                    ]
                result["status"] = "changed" if field_changes else "unchanged"
                result["changes"] = field_changes
                if field_changes:
                    changes.append({"reference": reference, "changes": field_changes})
            except Exception as error:
                result["status"] = "error"
                result["error"] = f"{type(error).__name__}: {error}"
                blocking_errors.append(f"{reference}: {result['error']}")
            page_results.append(result)

    status = "failed" if blocking_errors else (
        "action_required" if changes else "passed"
    )
    return {
        "status": status,
        "generated_at": generated_at,
        "source_id": SOURCE_ID,
        "published_record_count": len(records),
        "audited_record_count": len(page_results),
        "changed_record_count": len(changes),
        "change_samples": changes[:20],
        "page_results": page_results,
        "warnings": ["published Japan release is empty"] if not records else [],
        "blocking_errors": blocking_errors,
    }
