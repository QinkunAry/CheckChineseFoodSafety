from __future__ import annotations

import io
import re
import zipfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable
from urllib.parse import urlparse

from .china_samr_probe import (
    AUTHORITY,
    SOURCE_ID,
    fetch_official,
    parse_notice_page,
    read_xlsx_table,
)
from .models import stable_id
from .quality import build_quality_report


Fetcher = Callable[[str], bytes]

MAINLAND_LOCATION_TOKENS = (
    "北京市", "天津市", "上海市", "重庆市",
    "河北省", "山西省", "辽宁省", "吉林省", "黑龙江省", "江苏省",
    "浙江省", "安徽省", "福建省", "江西省", "山东省", "河南省",
    "湖北省", "湖南省", "广东省", "海南省", "四川省", "贵州省",
    "云南省", "陕西省", "甘肃省", "青海省",
    "内蒙古自治区", "广西壮族自治区", "西藏自治区",
    "宁夏回族自治区", "新疆维吾尔自治区",
)


def _clean(value: str) -> str:
    value = re.sub(r"\s+", " ", value or "").strip()
    return "" if value in {"/", "—", "-"} else value


def normalize_excel_date(value: str) -> str | None:
    value = _clean(value)
    if not value:
        return None
    if re.fullmatch(r"\d+(?:\.\d+)?", value):
        serial = float(value)
        if not 1 <= serial <= 100_000:
            raise ValueError(f"Excel date serial out of range: {value}")
        return (datetime(1899, 12, 30) + timedelta(days=serial)).date().isoformat()
    normalized = value.replace("年", "-").replace("月", "-").replace("日", "")
    normalized = normalized.replace("/", "-").replace(".", "-")
    match = re.search(r"(20\d{2})-(\d{1,2})-(\d{1,2})", normalized)
    if not match:
        raise ValueError(f"unsupported production date: {value}")
    return datetime(
        int(match.group(1)), int(match.group(2)), int(match.group(3))
    ).date().isoformat()


def has_mainland_producer_evidence(location: str) -> bool:
    return any(token in location for token in MAINLAND_LOCATION_TOKENS)


def product_category(food_subcategory: str, workbook_title: str = "") -> str:
    text = f"{workbook_title} {food_subcategory}"
    rules = (
        ("special_dietary_foods", ("特殊膳食", "婴幼儿", "孕妇", "运动营养")),
        ("health_foods", ("保健食品",)),
        ("alcoholic_beverages", ("酒类", "白酒", "葡萄酒", "啤酒", "黄酒")),
        ("beverages", ("饮料", "饮用水", "果汁", "固体饮料")),
        ("meat_and_poultry", ("肉制品", "畜禽肉", "鸡", "鸭", "猪肉", "牛肉", "羊肉")),
        ("seafood", ("水产", "鱼", "虾", "蟹")),
        ("dairy_and_eggs", ("乳制品", "乳粉", "奶", "蛋制品")),
        ("fruit", ("水果制品", "水果", "蜜饯")),
        ("vegetables", ("蔬菜制品", "蔬菜", "食用菌")),
        ("oils_and_fats", ("食用油", "油脂",)),
        ("spices_and_condiments", ("调味品", "酱油", "食醋", "香辛料")),
        ("nuts_and_seeds", ("炒货", "坚果", "籽类")),
        ("confectionery", ("糖果", "巧克力", "食糖")),
        ("bakery_and_cereal_products", ("糕点", "饼干", "粮食加工", "淀粉", "谷物")),
        ("prepared_foods", ("方便食品", "罐头", "豆制品", "餐饮食品", "膨化食品")),
    )
    for category, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return category
    return "other_food"


def hazard_tags(failures: list[dict[str, str]], remarks: list[str]) -> list[str]:
    text = " ".join(
        [value for failure in failures for value in failure.values()] + remarks
    )
    rules = (
        ("microbiological", ("菌落总数", "大肠菌群", "霉菌", "酵母", "沙门氏菌", "李斯特", "金黄色葡萄球菌", "微生物")),
        ("chemical", ("农药", "兽药", "铅", "镉", "汞", "砷", "二氧化硫", "黄曲霉毒素", "真菌毒素", "防腐剂", "甜味剂", "着色剂", "胭脂红", "苋菜红", "柠檬黄", "日落黄", "酸价", "过氧化值", "苯并[a]芘", "铝的残留量")),
        ("allergen", ("过敏原", "致敏")),
        ("labeling", ("标签", "标示要求", "酒精度")),
        ("adulteration", ("异物", "冒用", "真实性", "掺假", "假冒")),
    )
    tags = [tag for tag, keywords in rules if any(keyword in text for keyword in keywords)]
    return tags or ["composition_or_quality"]


def _value(row: list[str], index: int | None) -> str:
    return _clean(row[index]) if index is not None and index < len(row) else ""


def _header_indexes(headers: list[str]) -> dict[str, list[int]]:
    result: dict[str, list[int]] = {}
    for index, header in enumerate(headers):
        result.setdefault(header, []).append(index)
    return result


def parse_workbook_samples(payload: bytes, *, filename: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    table = read_xlsx_table(payload, filename=filename)
    headers: list[str] = table["headers"]
    rows: list[list[str]] = table["rows"]
    indexes = _header_indexes(headers)

    def first(header: str) -> int | None:
        values = indexes.get(header, [])
        return values[0] if values else None

    remarks_indexes = indexes.get("备注", [])
    field_indexes = {
        "sequence": first("序号"),
        "producer_name": first("标称生产企业名称"),
        "producer_location": first("标称生产企业地址"),
        "sampled_business_name": first("被抽样单位名称"),
        "sampled_business_location": first("被抽样单位地址"),
        "product_name": first("样品名称"),
        "specification": first("规格型号"),
        "trademark": first("商标"),
        "production_date_raw": first("生产日期"),
        "shelf_life": first("保质期"),
        "inspection_institution": first("检验机构"),
        "food_subcategory": first("食品细类"),
        "sampling_number": first("抽样编号"),
    }
    failure_indexes = {
        "item": first("不合格项目"),
        "measured_value": first("检验值"),
        "standard_value": first("标准值"),
        "label_requirement": first("标签标注要求"),
    }
    if field_indexes["sampling_number"] is None or field_indexes["product_name"] is None:
        raise ValueError(f"{filename} is missing sampling number or product name columns")

    samples: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    def finish() -> None:
        nonlocal current
        if current is None:
            return
        if not current["sampling_number"]:
            raise ValueError(
                f"{filename} sequence {current['sequence'] or '?'} has no sampling number"
            )
        if not current["product_name"]:
            raise ValueError(f"{filename} {current['sampling_number']} has no product name")
        if not current["failures"]:
            raise ValueError(f"{filename} {current['sampling_number']} has no failed item")
        raw_date = current.pop("production_date_raw")
        current["production_date"] = normalize_excel_date(raw_date)
        current["production_date_source"] = raw_date
        current["remarks"] = list(dict.fromkeys(current["remarks"]))
        current["failures"] = list(
            {tuple(sorted(failure.items())): failure for failure in current["failures"]}.values()
        )
        samples.append(current)
        current = None

    for row_number, row in enumerate(rows, start=table["header_row"] + 1):
        sequence = _value(row, field_indexes["sequence"])
        sampling_number = _value(row, field_indexes["sampling_number"])
        if current is not None:
            sequence_changed = bool(sequence and current["sequence"] and sequence != current["sequence"])
            sampling_changed = bool(
                sampling_number
                and current["sampling_number"]
                and sampling_number != current["sampling_number"]
            )
            if sequence_changed or sampling_changed:
                finish()
        if current is None:
            current = {
                "sequence": sequence,
                "sampling_number": sampling_number,
                "producer_name": "",
                "producer_location": "",
                "sampled_business_name": "",
                "sampled_business_location": "",
                "product_name": "",
                "specification": "",
                "trademark": "",
                "production_date_raw": "",
                "shelf_life": "",
                "inspection_institution": "",
                "food_subcategory": "",
                "workbook_title": table["title"],
                "source_attachment_name": filename,
                "source_row_count": 0,
                "remarks": [],
                "failures": [],
            }
        current["source_row_count"] += 1
        if sequence and not current["sequence"]:
            current["sequence"] = sequence
        if sampling_number and not current["sampling_number"]:
            current["sampling_number"] = sampling_number

        for field, index in field_indexes.items():
            if field in {"sequence", "sampling_number"}:
                continue
            value = _value(row, index)
            if not value:
                continue
            existing = current[field]
            if existing and existing != value:
                raise ValueError(
                    f"{filename} row {row_number} conflicts on {field}: {existing!r} != {value!r}"
                )
            current[field] = value

        for index in remarks_indexes:
            value = _value(row, index)
            if value:
                current["remarks"].append(value)

        item = _value(row, failure_indexes["item"])
        if item:
            current["failures"].append(
                {
                    field: _value(row, index)
                    for field, index in failure_indexes.items()
                }
            )
    finish()
    return samples, {
        "filename": filename,
        "workbook_title": table["title"],
        "physical_row_count": len(rows),
        "sample_count": len(samples),
        "continuation_row_count": len(rows) - len(samples),
    }


def parse_attachment_samples(payload: bytes, *, filename: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    suffix = PurePosixPath(filename).suffix.lower()
    if suffix == ".xlsx":
        samples, diagnostic = parse_workbook_samples(payload, filename=filename)
        return samples, [diagnostic]
    if suffix != ".zip":
        raise ValueError(f"unsupported SAMR candidate attachment: {filename}")
    samples: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = sorted(name for name in archive.namelist() if name.lower().endswith(".xlsx"))
        if not names:
            raise ValueError(f"{filename} contains no XLSX workbooks")
        for name in names:
            workbook_samples, diagnostic = parse_workbook_samples(
                archive.read(name), filename=name
            )
            samples.extend(workbook_samples)
            diagnostics.append(diagnostic)
    return samples, diagnostics


def _reason(failure: dict[str, str]) -> str:
    parts = [failure["item"]]
    labels = (
        ("measured_value", "检验值"),
        ("standard_value", "标准值"),
        ("label_requirement", "标签标注要求"),
    )
    parts.extend(f"{label}：{failure[field]}" for field, label in labels if failure[field])
    return "；".join(parts)


def normalize_candidate(
    sample: dict[str, Any],
    *,
    notice_url: str,
    event_date: str,
    retrieved_at: str,
) -> dict[str, Any]:
    source_record_id = sample["sampling_number"]
    reasons = [_reason(failure) for failure in sample["failures"]]
    reasons.extend(f"备注：{remark}" for remark in sample["remarks"])
    return {
        "id": stable_id(SOURCE_ID, source_record_id),
        "source_id": SOURCE_ID,
        "source_record_id": source_record_id,
        "authority": AUTHORITY,
        "authority_region": "CN",
        "action_type": "inspection_failure",
        "event_date": event_date,
        "origin_country": "unknown",
        "market_country": "CN",
        "regulatory_scope": "domestic_market",
        "producer_name": sample["producer_name"],
        "producer_location": sample["producer_location"],
        "product_code": "",
        "product_category": product_category(
            sample["food_subcategory"], sample["workbook_title"]
        ),
        "product_name": sample["product_name"],
        "reasons": reasons,
        "hazard_tags": hazard_tags(sample["failures"], sample["remarks"]),
        "source_url": notice_url,
        "retrieved_at": retrieved_at,
    }


def build_candidate_report(
    *,
    samples: list[dict[str, Any]],
    diagnostics: list[dict[str, Any]],
    notice_url: str,
    event_date: str,
    schema: dict[str, Any],
    retrieved_at: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    generated_at = retrieved_at or datetime.now(timezone.utc).isoformat()
    blocking_errors: list[str] = []
    candidates: list[dict[str, Any]] = []
    for sample in samples:
        try:
            candidates.append(
                normalize_candidate(
                    sample,
                    notice_url=notice_url,
                    event_date=event_date,
                    retrieved_at=generated_at,
                )
            )
        except Exception as error:
            blocking_errors.append(
                f"sample parse failed: {sample.get('sampling_number') or '?'}: "
                f"{type(error).__name__}: {error}"
            )
    source_ids = [sample["sampling_number"] for sample in samples]
    duplicate_source_id_count = len(source_ids) - len(set(source_ids))
    if duplicate_source_id_count:
        blocking_errors.append(
            f"duplicate sampling number count: {duplicate_source_id_count}"
        )
    quality = build_quality_report(candidates, schema, source_id=SOURCE_ID, min_records=0)
    blocking_errors.extend(str(error) for error in quality["blocking_errors"])
    return {
        "status": "failed" if blocking_errors else "passed",
        "generated_at": generated_at,
        "source_id": SOURCE_ID,
        "regulatory_scope": "domestic_market",
        "market_country": "CN",
        "notice_url": notice_url,
        "event_date": event_date,
        "workbook_count": len(diagnostics),
        "physical_row_count": sum(item["physical_row_count"] for item in diagnostics),
        "continuation_row_count": sum(item["continuation_row_count"] for item in diagnostics),
        "sample_count": len(samples),
        "candidate_count": len(candidates),
        "unique_sampling_number_count": len(set(source_ids)),
        "duplicate_sampling_number_count": duplicate_source_id_count,
        "origin_country_counts": dict(sorted(Counter(item["origin_country"] for item in candidates).items())),
        "mainland_producer_location_count": sum(
            has_mainland_producer_evidence(sample["producer_location"])
            for sample in samples
        ),
        "workbooks": diagnostics,
        "candidate_samples": [
            {
                "source_record_id": item["source_record_id"],
                "product_name": item["product_name"],
                "origin_country": item["origin_country"],
                "product_category": item["product_category"],
                "hazard_tags": item["hazard_tags"],
            }
            for item in candidates[:10]
        ],
        "schema_error_count": quality["schema_error_count"],
        "schema_error_samples": quality["schema_error_samples"],
        "duplicate_id_count": quality["duplicate_id_count"],
        "product_categories": quality["product_categories"],
        "hazard_tags": quality["hazard_tags"],
        "blocking_errors": blocking_errors,
    }, candidates


def candidate_china_samr(
    *,
    notice_url: str,
    schema: dict[str, Any],
    notice_payload: bytes | None = None,
    local_attachments: list[Path] | None = None,
    fetcher: Fetcher = fetch_official,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    notice = parse_notice_page(
        notice_payload if notice_payload is not None else fetcher(notice_url),
        url=notice_url,
    )
    if not notice["published_date"]:
        raise ValueError("SAMR notice does not expose a publication date")

    attachment_payloads: list[tuple[str, bytes]] = []
    if local_attachments:
        attachment_payloads.extend((path.name, path.read_bytes()) for path in local_attachments)
    else:
        for attachment in notice["attachments"]:
            filename = PurePosixPath(urlparse(attachment["url"]).path).name
            attachment_payloads.append((filename, fetcher(attachment["url"])))
    if not attachment_payloads:
        raise ValueError("SAMR candidate run has no XLSX or ZIP attachments")

    samples: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    for filename, payload in attachment_payloads:
        attachment_samples, attachment_diagnostics = parse_attachment_samples(
            payload, filename=filename
        )
        samples.extend(attachment_samples)
        diagnostics.extend(attachment_diagnostics)
    return build_candidate_report(
        samples=samples,
        diagnostics=diagnostics,
        notice_url=notice_url,
        event_date=notice["published_date"],
        schema=schema,
    )
