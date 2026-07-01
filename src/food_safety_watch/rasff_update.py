from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse

from .quality import (
    build_quality_report,
    load_schema,
    read_jsonl,
    write_json_file,
    write_jsonl_file,
)
from .rasff_probe import DATASET_URL, SEARCH_PAGE_URL, SOURCE_ID
from .update import QualityCheckFailed


AUTHORITY = "European Commission, Directorate-General for Health and Food Safety (DG SANTE)"
DATASET_TITLE = "Food and Feed Alert Notifications / RASFF Window"
LICENSE_NAME = "Creative Commons Attribution 4.0 International (CC BY 4.0)"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
LEGAL_NOTICE_URL = "https://commission.europa.eu/legal-notice_en"
PROJECT_CHANGES = [
    "selected China-origin human-food notifications",
    "normalized fields and dates",
    "added stable IDs, lifecycle status and deterministic search labels",
]
REQUIRED_DETAIL_FIELDS = (
    "record_status",
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
REFERENCE_RE = re.compile(r"\d{4}\.\d+")


def _valid_source_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    parts = parsed.path.strip("/").split("/")
    return (
        parsed.scheme == "https"
        and parsed.netloc == "webgate.ec.europa.eu"
        and len(parts) == 4
        and parts[:3] == ["rasff-window", "screen", "notification"]
        and parts[3].isdigit()
        and not parsed.query
        and not parsed.fragment
    )


def _validate_approved_references(
    records: list[dict[str, Any]], approved_references: list[str] | None
) -> list[str]:
    approved = sorted(
        set(value.strip() for value in approved_references or [] if value.strip())
    )
    actual = sorted(
        record["source_record_id"]
        for record in records
        if isinstance(record.get("source_record_id"), str)
    )
    if len(actual) != len(records) or len(set(actual)) != len(actual):
        raise ValueError("RASFF release requires one unique source_record_id per record")
    invalid = [reference for reference in actual + approved if not REFERENCE_RE.fullmatch(reference)]
    if invalid:
        raise ValueError(f"invalid RASFF release references: {sorted(set(invalid))}")
    if approved != actual:
        missing = sorted(set(actual) - set(approved))
        extra = sorted(set(approved) - set(actual))
        raise ValueError(
            "approved RASFF references must exactly match the release records; "
            f"missing approvals={missing}; approvals without records={extra}"
        )
    return approved


def merge_reviewed_release(
    *,
    baseline_records: list[dict[str, Any]],
    reviewed_records: list[dict[str, Any]],
    approved_references: list[str] | None,
    remove_references: list[str] | None = None,
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    approved = _validate_approved_references(reviewed_records, approved_references)
    baseline_references = [
        record.get("source_record_id")
        for record in baseline_records
        if isinstance(record.get("source_record_id"), str)
    ]
    if len(baseline_references) != len(baseline_records) or len(set(baseline_references)) != len(
        baseline_references
    ):
        raise ValueError("published RASFF baseline has missing or duplicate references")
    removed = sorted(
        set(value.strip() for value in remove_references or [] if value.strip())
    )
    invalid_removed = [value for value in removed if not REFERENCE_RE.fullmatch(value)]
    if invalid_removed:
        raise ValueError(f"invalid RASFF removal references: {invalid_removed}")
    unknown_removed = sorted(set(removed) - set(baseline_references))
    if unknown_removed:
        raise ValueError(f"cannot remove unpublished RASFF references: {unknown_removed}")
    overlap = sorted(set(removed) & set(approved))
    if overlap:
        raise ValueError(f"RASFF references cannot be approved and removed together: {overlap}")
    if not reviewed_records and not removed:
        raise ValueError("incremental RASFF release has no reviewed additions or removals")

    merged = {
        str(record["source_record_id"]): dict(record) for record in baseline_records
    }
    for reference in removed:
        del merged[reference]
    for record in reviewed_records:
        merged[str(record["source_record_id"])] = dict(record)
    return [merged[key] for key in sorted(merged)], approved, removed


def build_release_metadata(
    report: dict[str, Any], records: list[dict[str, Any]]
) -> dict[str, Any]:
    generated_at = str(report["generated_at"])
    year = generated_at[:4]
    return {
        "source_id": SOURCE_ID,
        "authority": AUTHORITY,
        "dataset_title": DATASET_TITLE,
        "release_scope": "explicitly_reviewed_subset",
        "release_mode": report.get("release_mode", "full_reviewed_input"),
        "approval_mode": "explicit_batch_allowlist_and_explicit_removals",
        "approved_references": report["approved_references"],
        "removed_references": report.get("removed_references", []),
        "release_references": report.get("release_references", []),
        "snapshot_retrieved_at": generated_at,
        "record_count": report["record_count"],
        "dataset_url": DATASET_URL,
        "human_search_url": SEARCH_PAGE_URL,
        "license": LICENSE_NAME,
        "license_url": LICENSE_URL,
        "legal_notice_url": LEGAL_NOTICE_URL,
        "changes_made": PROJECT_CHANGES,
        "attribution": (
            f"Source: © European Union, 1995–{year}; {AUTHORITY}, {DATASET_TITLE}. "
            "Retrieved from the linked official notifications and dataset. Source "
            "material is licensed under CC BY 4.0. This project selected and "
            "normalized records and added project metadata; changes were made. "
            "The European Commission and RASFF do not endorse this project."
        ),
        "record_provenance": [
            {
                "id": record["id"],
                "reference": record["source_record_id"],
                "source_url": record["source_url"],
                "retrieved_at": record["retrieved_at"],
                "official_last_update": record["official_last_update"],
                "record_status": record["record_status"],
            }
            for record in records
        ],
    }


def build_rasff_release(
    *,
    records: list[dict[str, Any]],
    approved_references: list[str],
    schema: dict[str, Any],
    baseline_records: list[dict[str, Any]] | None = None,
    generated_at: str | None = None,
    min_records: int = 1,
    max_records: int = 100,
    max_drop_fraction: float = 0.25,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if min_records < 1 or max_records < 1 or min_records > max_records:
        raise ValueError("RASFF release limits must satisfy 1 <= min_records <= max_records")
    timestamp = generated_at or datetime.now(timezone.utc).isoformat()
    release_records = [dict(record) for record in records]
    approved = _validate_approved_references(release_records, approved_references)

    previous = baseline_records or []
    first_seen = {
        record.get("id"): record.get("retrieved_at")
        for record in previous
        if isinstance(record.get("id"), str) and isinstance(record.get("retrieved_at"), str)
    }
    for record in release_records:
        previous_retrieved_at = first_seen.get(record.get("id"))
        if previous_retrieved_at:
            record["retrieved_at"] = previous_retrieved_at

    quality = build_quality_report(
        release_records,
        schema,
        source_id=SOURCE_ID,
        baseline_count=len(previous) if baseline_records is not None else None,
        min_records=min_records,
        max_drop_fraction=max_drop_fraction,
    )
    blocking_errors = list(quality["blocking_errors"])
    if len(release_records) > max_records:
        blocking_errors.append(
            f"record count {len(release_records)} exceeds reviewed-release maximum {max_records}"
        )
    for index, record in enumerate(release_records):
        reference = record.get("source_record_id", f"index {index}")
        if record.get("source_id") != SOURCE_ID:
            blocking_errors.append(f"{reference}: source_id must be {SOURCE_ID}")
        if record.get("origin_country") != "CN":
            blocking_errors.append(f"{reference}: origin_country must be CN")
        if record.get("regulatory_scope") != "origin_based":
            blocking_errors.append(f"{reference}: regulatory_scope must be origin_based")
        if record.get("action_type") != "rasff_notification":
            blocking_errors.append(f"{reference}: action_type must be rasff_notification")
        if record.get("record_status") != "active":
            blocking_errors.append(f"{reference}: only active records may be published")
        if record.get("official_notification_status") != "ec_validated":
            blocking_errors.append(
                f"{reference}: official notification status must be ec_validated"
            )
        if not _valid_source_url(record.get("source_url")):
            blocking_errors.append(f"{reference}: source_url is not an official detail page")
        missing = [field for field in REQUIRED_DETAIL_FIELDS if field not in record]
        if missing:
            blocking_errors.append(
                f"{reference}: missing detail-enriched fields: {', '.join(missing)}"
            )

    report = dict(quality)
    report.update({
        "status": "failed" if blocking_errors else "passed",
        "generated_at": timestamp,
        "release_scope": "explicitly_reviewed_subset",
        "approved_references": approved,
        "release_references": approved,
        "removed_references": [],
        "release_mode": "full_reviewed_input",
        "maximum_records": max_records,
        "maximum_drop_fraction": max_drop_fraction,
        "active_record_count": sum(
            record.get("record_status") == "active" for record in release_records
        ),
        "blocking_errors": blocking_errors,
    })
    return report, release_records


def _atomic_publish_pair(
    records: list[dict[str, Any]],
    metadata: dict[str, Any],
    output: Path,
    metadata_path: Path,
) -> None:
    if output.resolve() == metadata_path.resolve():
        raise ValueError("RASFF data and metadata paths must be different")
    output.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    data_stage = output.with_name(f".{output.name}.tmp")
    metadata_stage = metadata_path.with_name(f".{metadata_path.name}.tmp")
    data_backup = output.with_name(f".{output.name}.bak")
    metadata_backup = metadata_path.with_name(f".{metadata_path.name}.bak")
    targets = ((output, data_backup), (metadata_path, metadata_backup))
    try:
        write_jsonl_file(records, data_stage)
        write_json_file(metadata, metadata_stage)
        for target, backup in targets:
            if target.exists():
                target.replace(backup)
        data_stage.replace(output)
        metadata_stage.replace(metadata_path)
    except Exception as error:
        restore_errors: list[str] = []
        for target, backup in reversed(targets):
            try:
                if backup.exists():
                    if target.exists():
                        target.unlink()
                    backup.replace(target)
            except Exception as restore_error:
                restore_errors.append(f"{target}: {restore_error}")
        if restore_errors:
            raise RuntimeError(
                f"publication failed ({error}); rollback also failed: "
                + "; ".join(restore_errors)
            ) from error
        raise
    finally:
        for temporary in (data_stage, metadata_stage):
            if temporary.exists():
                temporary.unlink()
        for target, backup in targets:
            if backup.exists() and target.exists():
                backup.unlink()


def publish_rasff_reviewed(
    *,
    input_path: Path,
    output: Path,
    report_path: Path,
    metadata_path: Path,
    schema_path: Path,
    approved_references: list[str] | None,
    merge_current: bool = False,
    remove_references: list[str] | None = None,
    removal_only: bool = False,
    min_records: int = 1,
    max_records: int = 100,
    max_drop_fraction: float = 0.25,
) -> dict[str, Any]:
    baseline_records = read_jsonl(output) if output.exists() else None
    try:
        if removal_only and not merge_current:
            raise ValueError("--removal-only requires --merge-current")
        if remove_references and not merge_current:
            raise ValueError("--remove-reference requires --merge-current")
        if removal_only and approved_references:
            raise ValueError("--removal-only cannot include approved additions")
        reviewed_records = [] if removal_only else read_jsonl(input_path)
        release_input = reviewed_records
        release_approvals = approved_references
        batch_approved: list[str] | None = None
        removed: list[str] = []
        if merge_current:
            if baseline_records is None:
                raise ValueError("--merge-current requires an existing published RASFF release")
            release_input, batch_approved, removed = merge_reviewed_release(
                baseline_records=baseline_records,
                reviewed_records=reviewed_records,
                approved_references=approved_references,
                remove_references=remove_references,
            )
            release_approvals = [
                str(record["source_record_id"]) for record in release_input
            ]
        report, records = build_rasff_release(
            records=release_input,
            approved_references=release_approvals,
            schema=load_schema(schema_path),
            baseline_records=baseline_records,
            min_records=min_records,
            max_records=max_records,
            max_drop_fraction=max_drop_fraction,
        )
        if merge_current:
            report.update({
                "release_mode": "incremental_merge",
                "approved_references": batch_approved,
                "release_references": [
                    str(record["source_record_id"]) for record in records
                ],
                "removed_references": removed,
                "reviewed_batch_record_count": len(reviewed_records),
            })
    except Exception as error:
        report = {
            "status": "failed",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_id": SOURCE_ID,
            "record_count": 0,
            "blocking_errors": [f"release input failed: {type(error).__name__}: {error}"],
        }
        write_json_file(report, report_path)
        raise QualityCheckFailed(report["blocking_errors"][0]) from error

    write_json_file(report, report_path)
    if report["status"] != "passed":
        raise QualityCheckFailed(
            "RASFF reviewed release failed quality checks: "
            + "; ".join(report["blocking_errors"])
        )

    metadata = build_release_metadata(report, records)
    try:
        _atomic_publish_pair(records, metadata, output, metadata_path)
    except Exception as error:
        detail = f"publication failed: {type(error).__name__}: {error}"
        report["status"] = "failed"
        report["blocking_errors"].append(detail)
        write_json_file(report, report_path)
        raise QualityCheckFailed(detail) from error
    return report
