from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .taiwan_probe import DATA_URL, SOURCE_ID, fetch_dataset, parse_dataset, stable_record_id


def load_record_state(path: Path) -> list[str]:
    if not path.exists():
        return []
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("record_ids"), list):
        raise ValueError(f"invalid Taiwan TFDA record state: {path}")
    record_ids = value["record_ids"]
    if not all(isinstance(record_id, str) and record_id for record_id in record_ids):
        raise ValueError(f"Taiwan TFDA state contains an invalid record ID: {path}")
    return sorted(set(record_ids))


def new_records(
    records: list[dict[str, str]],
    previous_ids: list[str],
) -> list[dict[str, str]]:
    previous = set(previous_ids)
    return sorted(
        (record for record in records if stable_record_id(record) not in previous),
        key=lambda record: stable_record_id(record),
    )


def build_inventory_report(
    records: list[dict[str, str]],
    previous_ids: list[str],
) -> dict[str, Any]:
    current = {stable_record_id(record) for record in records}
    previous = set(previous_ids)
    new_ids = sorted(current - previous)
    removed_ids = sorted(previous - current)
    return {
        "status": "changed" if new_ids or removed_ids else "unchanged",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_id": SOURCE_ID,
        "data_url": DATA_URL,
        "identity_model": "canonical_full_record_sha256",
        "baseline_count": len(previous),
        "current_count": len(current),
        "new_record_count": len(new_ids),
        "new_record_ids": new_ids,
        "removed_record_count": len(removed_ids),
        "removed_record_ids": removed_ids,
        "warnings": [
            "TFDA supplies no native row ID; an amended row appears as one removed hash and one new hash."
        ],
    }


def inventory_taiwan_tfda(
    *,
    state_path: Path,
    payload: bytes | str | None = None,
) -> tuple[dict[str, Any], list[str]]:
    records = parse_dataset(payload if payload is not None else fetch_dataset())
    current_ids = sorted(stable_record_id(record) for record in records)
    return build_inventory_report(records, load_record_state(state_path)), current_ids


def write_record_state(
    record_ids: list[str],
    path: Path,
    *,
    created_at: str | None = None,
) -> None:
    value = {
        "source_id": SOURCE_ID,
        "data_url": DATA_URL,
        "created_at": created_at or datetime.now(timezone.utc).isoformat(),
        "identity_model": "canonical_full_record_sha256",
        "record_count": len(set(record_ids)),
        "record_ids": sorted(set(record_ids)),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
