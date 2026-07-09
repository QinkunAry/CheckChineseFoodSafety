from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .classification import classify_reasons
from .models import stable_id
from .rasff_probe import (
    AUTHORITY,
    AUTHORITY_REGION,
    SOURCE_ID,
    JsonFetcher,
    fetch_public_json,
    notification_url,
)


DETAIL_API_TEMPLATE = (
    "https://webgate.ec.europa.eu/rasff-window/backend/public/"
    "notification/view/id/{notification_id}/en/"
)
EXCLUDED_PRODUCT_CATEGORIES = {
    "food contact materials",
}


def detail_api_url(notification_id: int) -> str:
    if not isinstance(notification_id, int) or notification_id < 1:
        raise ValueError("RASFF detail ID must be a positive integer")
    return DETAIL_API_TEMPLATE.format(notification_id=notification_id)


def fetch_detail(
    notification_id: int,
    *,
    fetcher: JsonFetcher = fetch_public_json,
) -> bytes:
    return fetcher(detail_api_url(notification_id), None)


def _object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"RASFF detail lacks {field}")
    return value


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"RASFF detail lacks {field}")
    return value.strip()


def _description(value: Any, field: str) -> str:
    return _text(_object(value, field).get("description"), f"{field}.description")


def parse_detail(
    payload: bytes | str,
    *,
    expected_id: int | None = None,
    expected_reference: str | None = None,
) -> dict[str, Any]:
    import json

    text = payload.decode("utf-8-sig") if isinstance(payload, bytes) else payload
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("RASFF detail root must be an object")
    notification_id = value.get("id")
    if not isinstance(notification_id, int) or notification_id < 1:
        raise ValueError("RASFF detail lacks a valid id")
    if expected_id is not None and notification_id != expected_id:
        raise ValueError(
            f"RASFF detail ID mismatch: {notification_id} != {expected_id}"
        )
    reference = _text(value.get("reference"), "reference")
    if expected_reference is not None and reference != expected_reference:
        raise ValueError(
            f"RASFF detail reference mismatch: {reference} != {expected_reference}"
        )
    subject = _text(value.get("subject"), "subject")
    validation_date = _text(value.get("ecValidationDate"), "ecValidationDate")
    last_update = _text(value.get("lastUpdate"), "lastUpdate")
    datetime.strptime(validation_date, "%d-%m-%Y %H:%M:%S")
    datetime.strptime(last_update, "%d-%m-%Y %H:%M:%S")

    product_type = _description(value.get("productType"), "productType")
    classification = _description(
        value.get("notificationClassification"), "notificationClassification"
    )
    basis = _description(value.get("notificationBasis"), "notificationBasis")
    product = _object(value.get("product"), "product")
    product_name = _text(product.get("description"), "product.description")
    category = _description(product.get("productCategory"), "product.productCategory")
    risk = _object(value.get("risk"), "risk")
    risk_decision = _text(risk.get("riskDecision"), "risk.riskDecision")
    status = _text(value.get("notificationStatus"), "notificationStatus")

    hazards_value = product.get("hazards") or []
    if not isinstance(hazards_value, list):
        raise ValueError("RASFF detail product.hazards must be a list")
    hazards: list[dict[str, str]] = []
    for index, hazard in enumerate(hazards_value):
        item = _object(hazard, f"product.hazards[{index}]")
        name = _text(item.get("name"), f"product.hazards[{index}].name")
        category_value = item.get("hazardCategory") or {}
        category_text = ""
        if category_value:
            category_text = _description(
                category_value, f"product.hazards[{index}].hazardCategory"
            )
        hazards.append(
            {
                "name": name,
                "category": category_text,
                "analytical_result": str(item.get("analyticalResult") or "").strip(),
                "unit": str(item.get("unit") or "").strip(),
                "maximum_permitted": str(item.get("maxPermittedLvl") or "").strip(),
                "sampling_date": str(item.get("samplingDate") or "").strip(),
            }
        )

    distribution = product.get("distributionStatus") or {}
    distribution_status = ""
    if distribution:
        distribution_status = _description(
            distribution, "product.distributionStatus"
        )
    measures_value = product.get("measures") or []
    if not isinstance(measures_value, list):
        raise ValueError("RASFF detail product.measures must be a list")
    measures: list[str] = []
    for index, measure in enumerate(measures_value):
        item = _object(measure, f"product.measures[{index}]")
        action = _description(
            item.get("actionTaken"), f"product.measures[{index}].actionTaken"
        )
        if action not in measures:
            measures.append(action)

    flags = value.get("organizationFlags")
    if not isinstance(flags, list) or not flags:
        raise ValueError("RASFF detail lacks organizationFlags")
    origin_codes: list[str] = []
    for index, flag_group in enumerate(flags):
        group = _object(flag_group, f"organizationFlags[{index}]")
        organization = _object(
            group.get("organization"), f"organizationFlags[{index}].organization"
        )
        code = _text(
            organization.get("code"), f"organizationFlags[{index}].organization.code"
        ).upper()
        notification_flags = group.get("notificationFlags")
        if not isinstance(notification_flags, list):
            raise ValueError(
                f"RASFF detail organizationFlags[{index}] lacks notificationFlags"
            )
        if any(
            isinstance(flag, dict) and flag.get("flagType") == "ORIGIN"
            for flag in notification_flags
        ) and code not in origin_codes:
            origin_codes.append(code)
    if not origin_codes:
        raise ValueError("RASFF detail has no explicit ORIGIN organization flag")

    followups_value = value.get("followups") or []
    if not isinstance(followups_value, list):
        raise ValueError("RASFF detail followups must be a list")
    followup_types: list[str] = []
    for index, followup in enumerate(followups_value):
        item = _object(followup, f"followups[{index}]")
        followup_type = _description(
            item.get("fupType"), f"followups[{index}].fupType"
        )
        if followup_type not in followup_types:
            followup_types.append(followup_type)

    return {
        "notification_id": notification_id,
        "reference": reference,
        "subject": subject,
        "event_date_raw": validation_date,
        "last_update_raw": last_update,
        "product_type": product_type,
        "product_name": product_name,
        "product_category": category,
        "classification": classification,
        "notification_basis": basis,
        "risk_decision": risk_decision,
        "notification_status": status,
        "distribution_status": distribution_status,
        "origin_codes": origin_codes,
        "hazards": hazards,
        "measures": measures,
        "followup_types": followup_types,
    }


def is_china_food_detail(detail: dict[str, Any]) -> bool:
    product_category = str(detail.get("product_category") or "").casefold()
    return (
        str(detail.get("product_type") or "").casefold() == "food"
        and "CN" in detail.get("origin_codes", [])
        and product_category not in EXCLUDED_PRODUCT_CATEGORIES
    )


def detail_hazard_tags(detail: dict[str, Any], reasons: list[str]) -> list[str]:
    categories = " ".join(
        str(hazard.get("category") or "").casefold()
        for hazard in detail.get("hazards", [])
    )
    tags: list[str] = []
    category_rules = {
        "microbiological": (
            "pathogenic micro-organisms",
            "microbial contaminants",
            "parasites",
        ),
        "chemical": (
            "pesticide residues",
            "mycotoxins",
            "heavy metals",
            "chemical contamination",
            "veterinary medicinal products",
            "environmental pollutants",
            "food additives and flavourings",
        ),
        "allergen": ("allergens",),
    }
    for tag, phrases in category_rules.items():
        if any(phrase in categories for phrase in phrases):
            tags.append(tag)
    classified = classify_reasons(reasons)
    for tag in classified:
        if tag != "other_or_unclassified" and tag not in tags:
            tags.append(tag)
    return tags or ["other_or_unclassified"]


def lifecycle_status(detail: dict[str, Any]) -> str:
    official_status = str(detail.get("notification_status") or "").casefold()
    followups = [
        str(value).casefold() for value in detail.get("followup_types", [])
    ]
    has_withdrawal_followup = any("withdrawal" in value for value in followups)
    if official_status == "ec_withdrawn":
        return "withdrawn"
    if official_status == "ec_validated" and not has_withdrawal_followup:
        return "active"
    return "review_required"


def normalize_detail(
    detail: dict[str, Any],
    *,
    retrieved_at: str | None = None,
) -> dict[str, Any] | None:
    if not is_china_food_detail(detail):
        return None
    reference = detail["reference"]
    hazard_names: list[str] = []
    for hazard in detail["hazards"]:
        if hazard["name"] not in hazard_names:
            hazard_names.append(hazard["name"])
    reasons = hazard_names or [detail["subject"]]
    return {
        "id": stable_id(SOURCE_ID, reference),
        "source_id": SOURCE_ID,
        "source_record_id": reference,
        "authority": AUTHORITY,
        "authority_region": AUTHORITY_REGION,
        "action_type": "rasff_notification",
        "event_date": datetime.strptime(
            detail["event_date_raw"], "%d-%m-%Y %H:%M:%S"
        ).date().isoformat(),
        "origin_country": "CN",
        "regulatory_scope": "origin_based",
        "producer_name": "",
        "producer_location": "",
        "product_code": "",
        "product_category": detail["product_category"],
        "product_name": detail["product_name"],
        "reasons": reasons,
        "hazard_tags": detail_hazard_tags(detail, reasons),
        "source_url": notification_url(detail["notification_id"]),
        "retrieved_at": retrieved_at or datetime.now(timezone.utc).isoformat(),
        "record_status": lifecycle_status(detail),
        "official_notification_classification": detail["classification"],
        "official_risk_decision": detail["risk_decision"],
        "official_notification_basis": detail["notification_basis"],
        "official_notification_status": detail["notification_status"],
        "official_distribution_status": detail["distribution_status"],
        "official_last_update": detail["last_update_raw"],
        "official_hazards": detail["hazards"],
        "official_measures": detail["measures"],
        "official_followup_types": detail["followup_types"],
    }
