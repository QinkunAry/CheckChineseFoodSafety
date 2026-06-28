from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .quality import (
    build_quality_report,
    load_schema,
    read_jsonl,
    write_json_file,
    write_jsonl_file,
)
from .taiwan_candidates import build_candidate_report
from .taiwan_probe import (
    DATASET_URL,
    DATA_URL,
    SEARCH_URL,
    SOURCE_ID,
    fetch_dataset,
    is_china_origin,
    parse_dataset,
)
from .update import QualityCheckFailed


AUTHORITY_ZH = "衛生福利部食品藥物管理署"
DATASET_TITLE_ZH = "不符合食品資訊資料集"
LICENSE_NAME = "政府資料開放授權條款-第1版"
LICENSE_URL = "https://data.gov.tw/license"


def _atomic_write_jsonl(records: list[dict[str, Any]], path: Path) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        write_jsonl_file(records, temporary)
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _atomic_write_json(value: dict[str, Any], path: Path) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        write_json_file(value, temporary)
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def build_release_metadata(report: dict[str, Any]) -> dict[str, Any]:
    generated_at = str(report["generated_at"])
    year = generated_at[:4]
    return {
        "source_id": SOURCE_ID,
        "authority": AUTHORITY_ZH,
        "dataset_title": DATASET_TITLE_ZH,
        "dataset_version": "not_specified_by_provider",
        "snapshot_retrieved_at": generated_at,
        "record_count": report["record_count"],
        "dataset_url": DATASET_URL,
        "download_url": DATA_URL,
        "human_search_url": SEARCH_URL,
        "license": LICENSE_NAME,
        "license_url": LICENSE_URL,
        "attribution": (
            f"資料提供：{AUTHORITY_ZH}，{year}，《{DATASET_TITLE_ZH}》"
            "（資料提供者未標示獨立版本號）；本專案提供標準化衍生資料。"
        ),
    }


def build_taiwan_release(
    *,
    payload: bytes | str,
    schema: dict[str, Any],
    retrieved_at: str | None = None,
    baseline_records: list[dict[str, Any]] | None = None,
    min_source_records: int = 2_000,
    min_records: int = 300,
    max_drop_fraction: float = 0.25,
    max_unclassified: int = 0,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if min_source_records < 0 or min_records < 0 or max_unclassified < 0:
        raise ValueError("release limits must be non-negative")
    generated_at = retrieved_at or datetime.now(timezone.utc).isoformat()
    source_records = parse_dataset(payload)
    candidate_report, records = build_candidate_report(
        records=source_records,
        schema=schema,
        retrieved_at=generated_at,
        current_count=len(source_records),
        scope="production_full_snapshot",
    )

    previous = baseline_records or []
    first_seen = {
        record.get("id"): record.get("retrieved_at")
        for record in previous
        if isinstance(record.get("id"), str) and isinstance(record.get("retrieved_at"), str)
    }
    for record in records:
        previous_retrieved_at = first_seen.get(record["id"])
        if previous_retrieved_at:
            record["retrieved_at"] = previous_retrieved_at

    quality = build_quality_report(
        records,
        schema,
        source_id=SOURCE_ID,
        baseline_count=len(previous) if baseline_records is not None else None,
        min_records=min_records,
        max_drop_fraction=max_drop_fraction,
    )
    blocking_errors = list(quality["blocking_errors"])
    if len(source_records) < min_source_records:
        blocking_errors.append(
            f"source record count {len(source_records)} is below minimum {min_source_records}"
        )
    if candidate_report["parse_error_count"]:
        blocking_errors.append(
            f"candidate parse error count: {candidate_report['parse_error_count']}"
        )
    unclassified_count = sum(
        "other_or_unclassified" in record.get("hazard_tags", []) for record in records
    )
    if unclassified_count > max_unclassified:
        blocking_errors.append(
            f"unclassified hazard count {unclassified_count} exceeds maximum {max_unclassified}"
        )

    report = dict(quality)
    report.update({
        "status": "failed" if blocking_errors else "passed",
        "generated_at": generated_at,
        "dataset_url": DATASET_URL,
        "data_url": DATA_URL,
        "source_record_count": len(source_records),
        "china_source_record_count": sum(is_china_origin(record) for record in source_records),
        "excluded_record_count": len(source_records) - len(records),
        "minimum_source_records": min_source_records,
        "maximum_drop_fraction": max_drop_fraction,
        "unclassified_hazard_count": unclassified_count,
        "maximum_unclassified_hazards": max_unclassified,
        "parse_error_count": candidate_report["parse_error_count"],
        "parse_error_samples": candidate_report["parse_error_samples"],
        "blocking_errors": blocking_errors,
    })
    return report, records


def update_taiwan_tfda(
    *,
    output: Path,
    report_path: Path,
    metadata_path: Path,
    schema_path: Path,
    input_path: Path | None = None,
    payload: bytes | None = None,
    min_source_records: int = 2_000,
    min_records: int = 300,
    max_drop_fraction: float = 0.25,
    max_unclassified: int = 0,
) -> dict[str, Any]:
    baseline_records = read_jsonl(output) if output.exists() else None
    try:
        source_payload = payload if payload is not None else (
            input_path.read_bytes() if input_path else fetch_dataset()
        )
        report, records = build_taiwan_release(
            payload=source_payload,
            schema=load_schema(schema_path),
            baseline_records=baseline_records,
            min_source_records=min_source_records,
            min_records=min_records,
            max_drop_fraction=max_drop_fraction,
            max_unclassified=max_unclassified,
        )
    except Exception as error:
        if isinstance(error, QualityCheckFailed):
            raise
        report = {
            "status": "failed",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_id": SOURCE_ID,
            "dataset_url": DATASET_URL,
            "data_url": DATA_URL,
            "record_count": 0,
            "blocking_errors": [f"fetch/parse failed: {type(error).__name__}: {error}"],
        }
        write_json_file(report, report_path)
        raise QualityCheckFailed(report["blocking_errors"][0]) from error

    write_json_file(report, report_path)
    if report["status"] != "passed":
        messages = "; ".join(report["blocking_errors"])
        raise QualityCheckFailed(f"Taiwan TFDA candidate failed quality checks: {messages}")

    metadata = build_release_metadata(report)
    try:
        _atomic_write_json(metadata, metadata_path)
        _atomic_write_jsonl(records, output)
    except Exception as error:
        detail = f"publication failed: {type(error).__name__}: {error}"
        report["status"] = "failed"
        report["blocking_errors"].append(detail)
        write_json_file(report, report_path)
        raise QualityCheckFailed(detail) from error
    return report
