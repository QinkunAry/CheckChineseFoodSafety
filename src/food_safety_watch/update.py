from __future__ import annotations

from pathlib import Path

from .fda import SOURCE_ID, download, parse_archive
from .quality import (
    build_quality_report,
    load_schema,
    read_jsonl,
    write_json_file,
    write_jsonl_file,
)


class QualityCheckFailed(RuntimeError):
    pass


def update_fda(
    *,
    output: Path,
    report_path: Path,
    schema_path: Path,
    country: str = "CN",
    archive: Path | None = None,
    payload: bytes | None = None,
    min_records: int = 1_000,
    max_drop_fraction: float = 0.25,
) -> dict[str, object]:
    archive_payload = payload if payload is not None else (
        archive.read_bytes() if archive else download()
    )
    safety_records = parse_archive(archive_payload, country=country)
    records = [record.to_dict() for record in safety_records]
    baseline_records = read_jsonl(output) if output.exists() else []
    baseline_count = len(baseline_records) if output.exists() else None
    first_seen = {
        record.get("id"): record.get("retrieved_at")
        for record in baseline_records
        if isinstance(record.get("id"), str) and isinstance(record.get("retrieved_at"), str)
    }
    for record in records:
        previous_retrieved_at = first_seen.get(record["id"])
        if previous_retrieved_at:
            record["retrieved_at"] = previous_retrieved_at
    schema = load_schema(schema_path)
    report = build_quality_report(
        records,
        schema,
        source_id=SOURCE_ID,
        baseline_count=baseline_count,
        min_records=min_records,
        max_drop_fraction=max_drop_fraction,
    )
    write_json_file(report, report_path)
    if report["status"] != "passed":
        messages = "; ".join(report["blocking_errors"])
        raise QualityCheckFailed(f"FDA candidate failed quality checks: {messages}")

    write_jsonl_file(records, output)
    return report
