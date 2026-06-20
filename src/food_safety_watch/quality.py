from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker


MAX_ERROR_SAMPLES = 50


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {error.msg}") from error
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: each JSONL value must be an object")
            records.append(value)
    return records


def load_schema(path: Path) -> dict[str, Any]:
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return schema


def _error_path(index: int, error_path: Iterable[object]) -> str:
    suffix = "".join(f"[{part!r}]" for part in error_path)
    return f"records[{index}]{suffix}"


def build_quality_report(
    records: list[dict[str, Any]],
    schema: dict[str, Any],
    *,
    source_id: str,
    baseline_count: int | None = None,
    min_records: int = 1,
    max_drop_fraction: float = 0.25,
) -> dict[str, Any]:
    if not 0 <= max_drop_fraction < 1:
        raise ValueError("max_drop_fraction must be at least 0 and less than 1")

    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    schema_errors: list[dict[str, Any]] = []
    schema_error_count = 0
    for index, record in enumerate(records):
        for error in validator.iter_errors(record):
            schema_error_count += 1
            if len(schema_errors) < MAX_ERROR_SAMPLES:
                schema_errors.append({
                    "path": _error_path(index, error.absolute_path),
                    "message": error.message,
                })

    ids = [record.get("id") for record in records if isinstance(record.get("id"), str)]
    duplicate_ids = sorted(value for value, count in Counter(ids).items() if count > 1)
    blocking_errors: list[str] = []
    if len(records) < min_records:
        blocking_errors.append(f"record count {len(records)} is below minimum {min_records}")
    if duplicate_ids:
        blocking_errors.append(f"found {len(duplicate_ids)} duplicate IDs")
    if schema_error_count:
        blocking_errors.append(f"found {schema_error_count} schema errors")

    count_change_percent: float | None = None
    if baseline_count is not None and baseline_count > 0:
        count_change_percent = round((len(records) - baseline_count) / baseline_count * 100, 2)
        minimum_allowed = baseline_count * (1 - max_drop_fraction)
        if len(records) < minimum_allowed:
            blocking_errors.append(
                f"record count dropped {abs(count_change_percent):.2f}% from baseline; "
                f"maximum allowed drop is {max_drop_fraction * 100:.2f}%"
            )

    categories = Counter(
        record.get("product_category") for record in records
        if isinstance(record.get("product_category"), str)
    )
    hazard_tags = Counter(
        tag for record in records for tag in record.get("hazard_tags", [])
        if isinstance(tag, str)
    )
    dates = sorted(
        record["event_date"] for record in records
        if isinstance(record.get("event_date"), str)
    )

    return {
        "status": "failed" if blocking_errors else "passed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_id": source_id,
        "record_count": len(records),
        "baseline_count": baseline_count,
        "count_change_percent": count_change_percent,
        "unique_id_count": len(set(ids)),
        "duplicate_id_count": len(duplicate_ids),
        "duplicate_id_samples": duplicate_ids[:10],
        "schema_error_count": schema_error_count,
        "schema_error_samples": schema_errors,
        "event_date_min": dates[0] if dates else None,
        "event_date_max": dates[-1] if dates else None,
        "product_categories": dict(sorted(categories.items())),
        "hazard_tags": dict(sorted(hazard_tags.items())),
        "blocking_errors": blocking_errors,
    }


def write_json_file(value: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")


def write_jsonl_file(records: Iterable[dict[str, Any]], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count
