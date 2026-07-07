from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .japan_candidates import MHLW_AUTHORITY
from .japan_probe import SOURCE_ID
from .quality import (
    build_quality_report,
    load_schema,
    read_jsonl,
    write_json_file,
    write_jsonl_file,
)
from .update import QualityCheckFailed


SYSTEM_TITLE = "食品衛生申請等システム 食品リコール公開情報"
INFORMATION_URL = (
    "https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/kenkou_iryou/"
    "shokuhin/kigu/index_00012.html"
)
TERMS_URL = "https://www.mhlw.go.jp/chosakuken/index.html"
LICENSE_NAME = "公共データ利用規約（第1.0版） / Public Data License 1.0"
LICENSE_URL = "https://www.digital.go.jp/resources/open_data/public_data_license_v1.0"


def mhlw_reference_from_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    parsed = urlparse(value)
    query = parse_qs(parsed.query)
    reference = query.get("p", [])
    interface = query.get("i", [])
    if (
        parsed.scheme != "https"
        or parsed.netloc != "i2fas.mhlw.go.jp"
        or parsed.path != "/faspub/_link.do"
        or reference == []
        or len(reference) != 1
        or not reference[0].startswith("RCL")
        or not reference[0][3:].isdigit()
        or interface != ["IO_S020502"]
        or parsed.fragment
    ):
        return None
    return reference[0]


def _approved_references(
    records: list[dict[str, Any]], approved_references: list[str] | None
) -> list[str]:
    approved = sorted(set(value.strip() for value in approved_references or [] if value.strip()))
    actual = sorted(
        record["source_record_id"]
        for record in records
        if isinstance(record.get("source_record_id"), str)
    )
    if len(actual) != len(records) or len(set(actual)) != len(actual):
        raise ValueError("Japan release requires one unique source_record_id per record")
    if approved != actual:
        raise ValueError(
            "approved MHLW references must exactly match release records; "
            f"missing={sorted(set(actual) - set(approved))}; "
            f"extra={sorted(set(approved) - set(actual))}"
        )
    return approved


def merge_reviewed_release(
    *,
    baseline_records: list[dict[str, Any]],
    reviewed_records: list[dict[str, Any]],
    approved_references: list[str] | None,
    remove_references: list[str] | None = None,
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    approved = _approved_references(reviewed_records, approved_references)
    baseline_refs = [record.get("source_record_id") for record in baseline_records]
    if not all(isinstance(value, str) for value in baseline_refs) or len(set(baseline_refs)) != len(
        baseline_refs
    ):
        raise ValueError("published Japan baseline has missing or duplicate references")
    removed = sorted(set(value.strip() for value in remove_references or [] if value.strip()))
    unknown = sorted(set(removed) - set(baseline_refs))
    if unknown:
        raise ValueError(f"cannot remove unpublished MHLW references: {unknown}")
    overlap = sorted(set(removed) & set(approved))
    if overlap:
        raise ValueError(f"MHLW references cannot be approved and removed together: {overlap}")
    if not reviewed_records and not removed:
        raise ValueError("incremental Japan release has no additions, corrections or removals")
    merged = {str(record["source_record_id"]): dict(record) for record in baseline_records}
    for reference in removed:
        del merged[reference]
    for record in reviewed_records:
        merged[str(record["source_record_id"])] = dict(record)
    return [merged[key] for key in sorted(merged)], approved, removed


def build_release_metadata(
    report: dict[str, Any], records: list[dict[str, Any]]
) -> dict[str, Any]:
    generated_at = str(report["generated_at"])
    return {
        "source_id": SOURCE_ID,
        "authority": MHLW_AUTHORITY,
        "system_title": SYSTEM_TITLE,
        "release_scope": "explicitly_reviewed_mhlw_linked_subset",
        "release_mode": report.get("release_mode", "full_reviewed_input"),
        "approval_mode": "explicit_mhlw_reference_allowlist",
        "approved_references": report["approved_references"],
        "removed_references": report.get("removed_references", []),
        "release_references": report.get("release_references", []),
        "snapshot_retrieved_at": generated_at,
        "record_count": report["record_count"],
        "information_url": INFORMATION_URL,
        "terms_url": TERMS_URL,
        "license": LICENSE_NAME,
        "license_url": LICENSE_URL,
        "changes_made": [
            "selected explicitly evidenced China-origin food recalls",
            "normalized fields and dates",
            "added stable IDs and deterministic product/hazard search labels",
        ],
        "attribution_ja": (
            f"出典：厚生労働省「{SYSTEM_TITLE}」（各公開情報URL）、"
            f"公共データ利用規約（第1.0版）（{LICENSE_URL}）、{generated_at}利用。"
            "本プロジェクトが中国産食品を選別し、項目・日付を標準化し、"
            "検索用分類を付与して加工・作成したものであり、厚生労働省又は"
            "日本国政府が作成・承認したものではありません。"
        ),
        "attribution_en": (
            f"Source: {MHLW_AUTHORITY}, {SYSTEM_TITLE}, linked record URLs, used "
            f"{generated_at} under Public Data License 1.0. This project selected "
            "China-origin food recalls, normalized fields and dates, and added "
            "search classifications. The processed dataset was not created or "
            "endorsed by MHLW or the Government of Japan."
        ),
        "record_provenance": [
            {
                "id": record["id"],
                "reference": record["source_record_id"],
                "source_url": record["source_url"],
                "retrieved_at": record["retrieved_at"],
            }
            for record in records
        ],
    }


def build_japan_release(
    *,
    records: list[dict[str, Any]],
    approved_references: list[str] | None,
    schema: dict[str, Any],
    baseline_records: list[dict[str, Any]] | None = None,
    generated_at: str | None = None,
    min_records: int = 1,
    max_records: int = 100,
    max_drop_fraction: float = 0.25,
    max_unclassified: int = 0,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if min_records < 0 or max_records < 1 or min_records > max_records:
        raise ValueError("Japan release limits must satisfy 0 <= min_records <= max_records")
    if max_unclassified < 0:
        raise ValueError("max_unclassified must not be negative")
    timestamp = generated_at or datetime.now(timezone.utc).isoformat()
    release_records = [dict(record) for record in records]
    approved = _approved_references(release_records, approved_references)

    previous = baseline_records or []
    first_seen = {
        record.get("id"): record.get("retrieved_at")
        for record in previous
        if isinstance(record.get("id"), str) and isinstance(record.get("retrieved_at"), str)
    }
    for record in release_records:
        if record.get("id") in first_seen:
            record["retrieved_at"] = first_seen[record["id"]]

    quality = build_quality_report(
        release_records,
        schema,
        source_id=SOURCE_ID,
        baseline_count=len(previous) if baseline_records is not None else None,
        min_records=min_records,
        max_drop_fraction=max_drop_fraction,
    )
    blocking_errors = list(quality["blocking_errors"])
    if min_records == 0 and not release_records:
        blocking_errors = [
            error for error in blocking_errors
            if not str(error).startswith("record count dropped")
        ]
    if len(release_records) > max_records:
        blocking_errors.append(f"record count exceeds reviewed maximum {max_records}")
    for record in release_records:
        reference = record.get("source_record_id")
        if record.get("source_id") != SOURCE_ID:
            blocking_errors.append(f"{reference}: invalid source_id")
        if record.get("authority") != MHLW_AUTHORITY:
            blocking_errors.append(f"{reference}: release must use MHLW authority")
        if record.get("origin_country") != "CN":
            blocking_errors.append(f"{reference}: origin_country must be CN")
        if record.get("action_type") != "recall":
            blocking_errors.append(f"{reference}: action_type must be recall")
        url_reference = mhlw_reference_from_url(record.get("source_url"))
        if url_reference != reference:
            blocking_errors.append(f"{reference}: MHLW source URL/reference mismatch")
    unclassified_count = sum(
        "other_or_unclassified" in record.get("hazard_tags", [])
        for record in release_records
    )
    if unclassified_count > max_unclassified:
        blocking_errors.append(
            f"unclassified hazard count {unclassified_count} exceeds maximum {max_unclassified}"
        )
    report = dict(quality)
    report.update({
        "status": "failed" if blocking_errors else "passed",
        "generated_at": timestamp,
        "release_scope": "explicitly_reviewed_mhlw_linked_subset",
        "approved_references": approved,
        "release_references": approved,
        "removed_references": [],
        "release_mode": "full_reviewed_input",
        "maximum_records": max_records,
        "maximum_drop_fraction": max_drop_fraction,
        "unclassified_hazard_count": unclassified_count,
        "maximum_unclassified_hazards": max_unclassified,
        "empty_release_explicitly_allowed": min_records == 0,
        "blocking_errors": blocking_errors,
    })
    return report, release_records


def _atomic_publish_pair(
    records: list[dict[str, Any]], metadata: dict[str, Any], output: Path, metadata_path: Path
) -> None:
    if output.resolve() == metadata_path.resolve():
        raise ValueError("Japan data and metadata paths must be different")
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
    except Exception:
        for target, backup in reversed(targets):
            if backup.exists():
                if target.exists():
                    target.unlink()
                backup.replace(target)
        raise
    finally:
        for path in (data_stage, metadata_stage):
            if path.exists():
                path.unlink()
        for target, backup in targets:
            if backup.exists() and target.exists():
                backup.unlink()


def publish_japan_reviewed(
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
    max_unclassified: int = 0,
) -> dict[str, Any]:
    baseline = read_jsonl(output) if output.exists() else None
    try:
        if removal_only and not merge_current:
            raise ValueError("--removal-only requires --merge-current")
        if remove_references and not merge_current:
            raise ValueError("--remove-reference requires --merge-current")
        if removal_only and approved_references:
            raise ValueError("--removal-only cannot include approved additions")
        reviewed = [] if removal_only else read_jsonl(input_path)
        release_input = reviewed
        release_approvals = approved_references
        batch_approved: list[str] | None = None
        removed: list[str] = []
        if merge_current:
            if baseline is None:
                raise ValueError("--merge-current requires an existing Japan release")
            release_input, batch_approved, removed = merge_reviewed_release(
                baseline_records=baseline,
                reviewed_records=reviewed,
                approved_references=approved_references,
                remove_references=remove_references,
            )
            release_approvals = [str(record["source_record_id"]) for record in release_input]
        report, records = build_japan_release(
            records=release_input,
            approved_references=release_approvals,
            schema=load_schema(schema_path),
            baseline_records=baseline,
            min_records=min_records,
            max_records=max_records,
            max_drop_fraction=max_drop_fraction,
            max_unclassified=max_unclassified,
        )
        if merge_current:
            report.update({
                "release_mode": "incremental_merge",
                "approved_references": batch_approved,
                "release_references": [str(record["source_record_id"]) for record in records],
                "removed_references": removed,
                "reviewed_batch_record_count": len(reviewed),
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
            "Japan reviewed release failed quality checks: "
            + "; ".join(report["blocking_errors"])
        )
    try:
        _atomic_publish_pair(records, build_release_metadata(report, records), output, metadata_path)
    except Exception as error:
        detail = f"publication failed: {type(error).__name__}: {error}"
        report["status"] = "failed"
        report["blocking_errors"].append(detail)
        write_json_file(report, report_path)
        raise QualityCheckFailed(detail) from error
    return report
