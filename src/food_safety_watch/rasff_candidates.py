from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .quality import build_quality_report
from .rasff_inventory import (
    DEFAULT_PAGE_SIZE,
    collect_rasff_notifications,
    load_inventory_state,
    notification_fingerprint,
)
from .rasff_probe import (
    SOURCE_ID,
    JsonFetcher,
    fetch_public_json,
    normalize_notification,
)
from .rasff_detail import detail_api_url, normalize_detail, parse_detail


REFERENCE_RE = re.compile(r"\d{4}\.\d+")


def _validate_references(references: list[str] | None) -> list[str]:
    result: list[str] = []
    for reference in references or []:
        value = reference.strip()
        if not REFERENCE_RE.fullmatch(value):
            raise ValueError(f"invalid RASFF reference: {reference!r}")
        if value not in result:
            result.append(value)
    return result


def select_candidate_notifications(
    *,
    notifications: list[dict[str, Any]],
    baseline: dict[str, dict[str, Any]],
    review_references: list[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    requested = _validate_references(review_references)
    current = {
        str(notification["reference"]).strip(): notification
        for notification in notifications
    }
    current_refs = set(current)
    baseline_refs = set(baseline)
    new_refs = sorted(current_refs - baseline_refs)
    removed_refs = sorted(baseline_refs - current_refs)
    changed_refs = sorted(
        reference
        for reference in current_refs & baseline_refs
        if notification_fingerprint(current[reference])
        != baseline[reference]["fingerprint"]
        or current[reference]["notifId"]
        != baseline[reference]["notification_id"]
    )
    missing_requested = sorted(set(requested) - current_refs)
    if missing_requested:
        raise ValueError(
            "requested RASFF references are not in the current scoped inventory: "
            + ", ".join(missing_requested)
        )
    selected_refs = requested if requested else sorted(set(new_refs + changed_refs))
    return [current[reference] for reference in selected_refs], {
        "scope": "explicit_review" if requested else "new_or_changed_since_baseline",
        "requested_references": requested,
        "new_references": new_refs,
        "changed_references": changed_refs,
        "removed_references": removed_refs,
        "selected_references": selected_refs,
    }


def _evidence_sample(notification: dict[str, Any]) -> dict[str, Any]:
    return {
        "notification_id": notification["notifId"],
        "reference": str(notification["reference"]).strip(),
        "event_date_raw": notification["ecValidationDate"],
        "subject": str(notification["subject"]).strip(),
        "notifying_country": notification["notifyingCountry"],
        "product_category": notification["productCategory"],
        "product_type": notification["productType"],
        "notification_classification": notification["notificationClassification"],
        "risk_decision": notification["riskDecision"],
        "origin_countries": notification["originCountries"],
    }


def _detail_evidence_sample(detail: dict[str, Any]) -> dict[str, Any]:
    return {
        "notification_id": detail["notification_id"],
        "reference": detail["reference"],
        "subject": detail["subject"],
        "product_name": detail["product_name"],
        "product_category": detail["product_category"],
        "product_type": detail["product_type"],
        "classification": detail["classification"],
        "notification_basis": detail["notification_basis"],
        "risk_decision": detail["risk_decision"],
        "notification_status": detail["notification_status"],
        "distribution_status": detail["distribution_status"],
        "origin_codes": detail["origin_codes"],
        "hazards": detail["hazards"],
        "measures": detail["measures"],
        "followup_types": detail["followup_types"],
    }


def build_candidate_report(
    *,
    selected: list[dict[str, Any]],
    selection: dict[str, Any],
    schema: dict[str, Any],
    baseline_count: int,
    current_count: int,
    details: list[dict[str, Any]] | None = None,
    generated_at: str | None = None,
    max_candidates: int = 100,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if max_candidates < 1:
        raise ValueError("RASFF max_candidates must be at least 1")
    timestamp = generated_at or datetime.now(timezone.utc).isoformat()
    blocking_errors: list[str] = []
    parse_error_samples: list[dict[str, str]] = []
    parse_error_count = 0
    candidates: list[dict[str, Any]] = []
    if len(selected) > max_candidates:
        blocking_errors.append(
            f"selected record count {len(selected)} exceeds maximum {max_candidates}; "
            "review and raise the limit explicitly"
        )
    else:
        if details is not None and len(details) != len(selected):
            blocking_errors.append(
                "detail record count does not match selected search records"
            )
        records_to_normalize = details if details is not None else selected
        for notification in records_to_normalize:
            try:
                candidate = (
                    normalize_detail(notification, retrieved_at=timestamp)
                    if details is not None
                    else normalize_notification(notification, retrieved_at=timestamp)
                )
                if candidate is None:
                    raise ValueError("notification is outside China human-food scope")
                candidates.append(candidate)
            except Exception as error:
                parse_error_count += 1
                reference = str(notification.get("reference") or "")
                detail = f"{type(error).__name__}: {error}"
                blocking_errors.append(
                    f"candidate parse failed for {reference}: {detail}"
                )
                if len(parse_error_samples) < 20:
                    parse_error_samples.append(
                        {"reference": reference, "error": detail}
                    )

    quality = build_quality_report(
        candidates,
        schema,
        source_id=SOURCE_ID,
        min_records=0,
    )
    blocking_errors.extend(str(error) for error in quality["blocking_errors"])
    return (
        {
            "status": "failed" if blocking_errors else "passed",
            "generated_at": timestamp,
            "source_id": SOURCE_ID,
            "scope": selection["scope"],
            "baseline_count": baseline_count,
            "current_count": current_count,
            "new_record_count": len(selection["new_references"]),
            "new_reference_samples": selection["new_references"][:50],
            "changed_record_count": len(selection["changed_references"]),
            "changed_reference_samples": selection["changed_references"][:50],
            "removed_record_count": len(selection["removed_references"]),
            "removed_reference_samples": selection["removed_references"][:50],
            "requested_references": selection["requested_references"],
            "selected_record_count": len(selected),
            "candidate_record_count": len(candidates),
            "maximum_candidates": max_candidates,
            "detail_enriched_count": len(details) if details is not None else 0,
            "withdrawn_record_count": sum(
                detail.get("notification_status") == "ec_withdrawn"
                for detail in details or []
            ),
            "evidence_samples": (
                [_detail_evidence_sample(item) for item in details[:20]]
                if details is not None
                else [_evidence_sample(item) for item in selected[:20]]
            ),
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


def candidate_rasff(
    *,
    state_path: Path,
    schema: dict[str, Any],
    review_references: list[str] | None = None,
    max_candidates: int = 100,
    fetcher: JsonFetcher = fetch_public_json,
    detail_fetcher: JsonFetcher | None = None,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    generated_at = datetime.now(timezone.utc).isoformat()
    try:
        notifications, diagnostics = collect_rasff_notifications(
            fetcher=fetcher,
            page_size=page_size,
        )
        if not diagnostics["complete_scan"]:
            raise ValueError("RASFF candidate generation requires a complete scan")
        baseline = load_inventory_state(state_path)
        selected, selection = select_candidate_notifications(
            notifications=notifications,
            baseline=baseline,
            review_references=review_references,
        )
        read_detail = detail_fetcher or fetcher
        details = [
            parse_detail(
                read_detail(detail_api_url(notification["notifId"]), None),
                expected_id=notification["notifId"],
                expected_reference=str(notification["reference"]).strip(),
            )
            for notification in selected
        ]
        return build_candidate_report(
            selected=selected,
            details=details,
            selection=selection,
            schema=schema,
            baseline_count=len(baseline),
            current_count=len(notifications),
            generated_at=generated_at,
            max_candidates=max_candidates,
        )
    except Exception as error:
        return (
            {
                "status": "failed",
                "generated_at": generated_at,
                "source_id": SOURCE_ID,
                "scope": (
                    "explicit_review"
                    if review_references
                    else "new_or_changed_since_baseline"
                ),
                "candidate_record_count": 0,
                "blocking_errors": [
                    f"RASFF candidate generation failed: "
                    f"{type(error).__name__}: {error}"
                ],
            },
            [],
        )
