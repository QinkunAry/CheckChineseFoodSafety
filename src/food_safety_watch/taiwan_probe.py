from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any


SOURCE_ID = "tw_tfda"
DATA_URL = "https://data.fda.gov.tw/data/opendata/export/52/json"
DATASET_URL = "https://data.gov.tw/dataset/6133"
SEARCH_URL = "https://www.fda.gov.tw/UnsafeFood/UnsafeFood.aspx?idx=0"
USER_AGENT = (
    "FoodSafetyWatch/0.1 "
    "(+https://github.com/QinkunAry/CheckChineseFoodSafety)"
)
REQUIRED_FIELDS = {
    "產地", "主旨", "原因", "進口商名稱", "貨品分類號列", "不合格原因暨檢出量詳細說明",
    "處置情形", "發布日期", "報驗受理日期",
}
CHINA_ORIGINS = {"中國大陸", "中國", "中華人民共和國"}
FOOD_ADDITIVE_TARIFF_PREFIXES = (
    "2836.30",  # sodium bicarbonate
    "3203.00",  # food colour preparations
    "3301.90",  # plant extracts and oleoresins
    "3802.90",  # food-processing mineral preparations
)


class TaiwanFetchError(RuntimeError):
    pass


def fetch_dataset(*, timeout: int = 120) -> bytes:
    curl = shutil.which("curl")
    if not curl:
        raise TaiwanFetchError("curl is required for Taiwan TFDA requests")
    command = [
        curl, "-L", "--fail", "--silent", "--show-error", "--ipv4", "--http1.1",
        "--retry", "3", "--retry-all-errors", "--connect-timeout", "20",
        "--max-time", str(timeout), "--user-agent", USER_AGENT, DATA_URL,
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True)
    except subprocess.CalledProcessError as error:
        detail = error.stderr.decode("utf-8", errors="replace").strip()
        raise TaiwanFetchError(f"Taiwan TFDA download failed: {detail or error}") from error
    if not result.stdout:
        raise TaiwanFetchError("Taiwan TFDA returned an empty dataset")
    return result.stdout


def parse_dataset(payload: bytes | str) -> list[dict[str, str]]:
    text = payload.decode("utf-8-sig") if isinstance(payload, bytes) else payload
    value = json.loads(text)
    if not isinstance(value, list):
        raise ValueError("Taiwan TFDA dataset root must be a list")
    records: list[dict[str, str]] = []
    for index, record in enumerate(value):
        if not isinstance(record, dict):
            raise ValueError(f"Taiwan TFDA record {index} is not an object")
        missing = REQUIRED_FIELDS - set(record)
        if missing:
            raise ValueError(f"Taiwan TFDA record {index} missing fields: {sorted(missing)}")
        records.append({str(key): str(item or "").strip() for key, item in record.items()})
    return records


def is_china_origin(record: dict[str, str]) -> bool:
    return record.get("產地", "").strip() in CHINA_ORIGINS


def is_human_food_candidate(record: dict[str, str]) -> bool:
    tariff_code = record.get("貨品分類號列", "").strip()
    if "容器具" in record.get("原因", ""):
        return False
    if tariff_code.startswith(FOOD_ADDITIVE_TARIFF_PREFIXES):
        return True
    match = re.match(r"\s*(\d{2})", tariff_code)
    if not match:
        return False
    chapter = int(match.group(1))
    if chapter == 23 or not 1 <= chapter <= 24:
        return False
    return True


def stable_record_id(record: dict[str, str]) -> str:
    canonical = json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


def normalize_date(value: str) -> str:
    return datetime.strptime(value, "%Y/%m/%d").date().isoformat()


def _sample(record: dict[str, str]) -> dict[str, Any]:
    return {
        "id": stable_record_id(record),
        "origin": record["產地"],
        "product_name": record["主旨"],
        "reason": record["原因"],
        "reason_detail": record["不合格原因暨檢出量詳細說明"][:500],
        "event_date": normalize_date(record["發布日期"]),
        "accepted_date": normalize_date(record["報驗受理日期"]),
        "importer": record["進口商名稱"],
        "manufacturer_or_exporter": record.get("製造廠或出口商名稱", ""),
        "tariff_code": record["貨品分類號列"],
        "disposition": record["處置情形"],
        "human_food_candidate": is_human_food_candidate(record),
        "source_url": SEARCH_URL,
    }


def build_taiwan_probe_report(
    *,
    payload: bytes | str | None = None,
    limit: int = 10,
    min_records: int = 2_000,
    min_china_records: int = 300,
) -> dict[str, Any]:
    if limit < 1 or min_records < 0 or min_china_records < 0:
        raise ValueError("probe limits must be non-negative and limit must be at least 1")
    generated_at = datetime.now(timezone.utc).isoformat()
    blocking_errors: list[str] = []
    try:
        records = parse_dataset(payload if payload is not None else fetch_dataset())
    except Exception as error:
        return {
            "status": "failed", "generated_at": generated_at, "source_id": SOURCE_ID,
            "dataset_url": DATASET_URL, "data_url": DATA_URL,
            "record_count": 0, "china_record_count": 0,
            "blocking_errors": [f"dataset fetch/parse failed: {type(error).__name__}: {error}"],
        }
    china = [record for record in records if is_china_origin(record)]
    food = [record for record in records if is_human_food_candidate(record)]
    china_food = [record for record in china if is_human_food_candidate(record)]
    ids = [stable_record_id(record) for record in records]
    invalid_dates: list[str] = []
    for record in records:
        try:
            normalize_date(record["發布日期"])
            normalize_date(record["報驗受理日期"])
        except ValueError:
            invalid_dates.append(record.get("主旨", ""))
    if len(records) < min_records:
        blocking_errors.append(f"record count {len(records)} below minimum {min_records}")
    if len(china) < min_china_records:
        blocking_errors.append(
            f"China-origin record count {len(china)} below minimum {min_china_records}"
        )
    if invalid_dates:
        blocking_errors.append(f"invalid date count: {len(invalid_dates)}")
    duplicate_count = len(ids) - len(set(ids))
    if duplicate_count:
        blocking_errors.append(f"duplicate stable ID count: {duplicate_count}")
    sorted_china_food = sorted(china_food, key=lambda item: item["發布日期"], reverse=True)
    sorted_non_china_food = sorted(
        (record for record in food if not is_china_origin(record)),
        key=lambda item: item["發布日期"], reverse=True,
    )
    dates = sorted(record["發布日期"] for record in records)
    return {
        "status": "failed" if blocking_errors else "passed",
        "generated_at": generated_at,
        "source_id": SOURCE_ID,
        "dataset_url": DATASET_URL,
        "data_url": DATA_URL,
        "search_url": SEARCH_URL,
        "record_count": len(records),
        "human_food_candidate_count": len(food),
        "china_record_count": len(china),
        "china_human_food_candidate_count": len(china_food),
        "minimum_records": min_records,
        "minimum_china_records": min_china_records,
        "duplicate_id_count": duplicate_count,
        "invalid_date_count": len(invalid_dates),
        "event_date_min": normalize_date(dates[0]) if dates else None,
        "event_date_max": normalize_date(dates[-1]) if dates else None,
        "china_samples": [_sample(record) for record in sorted_china_food[:limit]],
        "non_china_samples": [_sample(record) for record in sorted_non_china_food[:2]],
        "blocking_errors": blocking_errors,
    }
