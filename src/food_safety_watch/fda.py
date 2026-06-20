from __future__ import annotations

import csv
import io
import json
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .classification import classify_reasons
from .models import SafetyRecord, stable_id


SOURCE_ID = "us_fda_import_refusals"
SOURCE_URL = "https://www.accessdata.fda.gov/scripts/importrefusals/"
DOWNLOAD_URL = (
    "https://www.accessdata.fda.gov/scripts/importrefusals/downloads/"
    "Import_Refusal_2024-present.zip"
)

# Human-food industries listed by FDA's official Product Code Builder.
# Animal food, food-service equipment, warehouses, drugs, cosmetics and devices
# are deliberately outside the MVP scope.
FOOD_INDUSTRIES: dict[str, str] = {
    "02": "grains_and_starches", "03": "bakery", "04": "pasta_and_noodles",
    "05": "cereal_and_breakfast_food", "07": "snacks", "09": "dairy",
    "12": "cheese", "13": "ice_cream", "14": "imitation_milk",
    "15": "eggs", "16": "seafood", "17": "meat_and_poultry",
    "18": "vegetable_protein", "20": "fruit", "21": "fruit",
    "22": "fruit", "23": "nuts_and_seeds", "24": "vegetables",
    "25": "vegetables", "26": "vegetable_oils", "27": "condiments",
    "28": "spices_and_salt", "29": "soft_drinks_and_water",
    "30": "beverage_bases", "31": "coffee_and_tea",
    "32": "alcoholic_beverages", "33": "candy", "34": "chocolate_and_cocoa",
    "35": "gelatin_and_dessert_mixes", "36": "sweeteners",
    "37": "prepared_meals_and_sauces", "38": "soups", "39": "prepared_salads",
    "40": "baby_food", "41": "meal_replacements", "42": "edible_insects",
    "45": "food_additives", "46": "food_additives",
}


def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Unable to decode FDA CSV")


def _clean_row(row: dict[str, str | None]) -> dict[str, str]:
    return {(key or "").strip().upper(): (value or "").strip() for key, value in row.items()}


def _read_csv(archive: zipfile.ZipFile, name: str) -> list[dict[str, str]]:
    text = _decode(archive.read(name))
    return [_clean_row(row) for row in csv.DictReader(io.StringIO(text))]


def _record_key(row: dict[str, str]) -> str:
    parts = [
        row.get("ENTRY_NUM", ""),
        row.get("RFRNC_DOC_ID", ""),
        row.get("LINE_NUM", ""),
        row.get("LINE_SFX_ID", ""),
        row.get("REFUSAL_DATE", ""),
    ]
    return "|".join(parts)


def _split_charge_ids(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def food_category(product_code: str) -> str | None:
    return FOOD_INDUSTRIES.get(product_code.strip()[:2])


def normalize_date(value: str) -> str:
    value = value.strip()
    for pattern in ("%d-%b-%y", "%d-%b-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, pattern).date().isoformat()
        except ValueError:
            continue
    return value


def parse_archive(payload: bytes, country: str = "CN") -> list[SafetyRecord]:
    retrieved_at = datetime.now(timezone.utc).isoformat()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        charge_name = next(
            (name for name in csv_names if "ACT_SECTION_CHARGES" in name.upper()), None
        )
        if charge_name is None:
            raise ValueError("FDA archive does not contain ACT_SECTION_CHARGES.CSV")

        charge_rows = _read_csv(archive, charge_name)
        charges = {
            row.get("ASC_ID", ""): row.get("CHRG_STMNT_TEXT", "")
            for row in charge_rows
            if row.get("ASC_ID")
        }

        data_names = [name for name in csv_names if name != charge_name]
        if not data_names:
            raise ValueError("FDA archive does not contain refusal CSV data")

        records: list[SafetyRecord] = []
        for name in data_names:
            for row in _read_csv(archive, name):
                if row.get("ISO_CNTRY_CODE", "").upper() != country.upper():
                    continue
                category = food_category(row.get("PRODUCT_CODE", ""))
                if category is None:
                    continue
                reason_ids = _split_charge_ids(row.get("REFUSAL_CHARGES", ""))
                reasons = [charges.get(reason_id, f"FDA charge ID {reason_id}") for reason_id in reason_ids]
                reasons = [reason for reason in reasons if reason]
                source_record_id = _record_key(row)
                location = ", ".join(
                    part for part in (
                        row.get("CITY_NAME", ""), row.get("PROVINCE_STATE", ""),
                        row.get("ISO_CNTRY_CODE", ""),
                    ) if part
                )
                records.append(SafetyRecord(
                    id=stable_id(SOURCE_ID, source_record_id),
                    source_id=SOURCE_ID,
                    source_record_id=source_record_id,
                    authority="U.S. Food and Drug Administration",
                    authority_region="US",
                    action_type="import_refusal",
                    event_date=normalize_date(row.get("REFUSAL_DATE", "")),
                    origin_country=row.get("ISO_CNTRY_CODE", ""),
                    producer_name=row.get("LGL_NAME", ""),
                    producer_location=location,
                    product_code=row.get("PRODUCT_CODE", ""),
                    product_category=category,
                    product_name=row.get("PRDCT_CODE_DESC_TEXT", ""),
                    reasons=reasons,
                    hazard_tags=classify_reasons(reasons),
                    source_url=SOURCE_URL,
                    retrieved_at=retrieved_at,
                ))
    return records


def download(url: str = DOWNLOAD_URL) -> bytes:
    curl = shutil.which("curl")
    if curl is not None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "fda-import-refusals.zip"
            subprocess.run(
                [curl, "-L", "--fail", "--max-time", "60", "-o", str(destination), url],
                check=True,
            )
            return destination.read_bytes()
    request = urllib.request.Request(url, headers={"User-Agent": "FoodSafetyWatch/0.1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def write_jsonl(records: Iterable[SafetyRecord], output: Path) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output.open("w", encoding="utf-8", newline="\n") as stream:
        for record in records:
            stream.write(json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count
