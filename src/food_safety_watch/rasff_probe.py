from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlparse

from .classification import classify_reasons
from .models import stable_id
from .quality import build_quality_report


SOURCE_ID = "eu_rasff"
AUTHORITY = "European Commission / DG SANTE / RASFF"
AUTHORITY_REGION = "EU"
PUBLIC_HOST = "webgate.ec.europa.eu"
DATA_EUROPA_HOST = "data.europa.eu"
DG_SANTE_DEVELOPER_HOST = "developer.datalake.sante.service.ec.europa.eu"
SEARCH_PAGE_URL = "https://webgate.ec.europa.eu/rasff-window/screen/search"
DATASET_URL = "https://data.europa.eu/data/datasets/restored_rasff~~1?locale=en"
CONFIG_URL = "https://webgate.ec.europa.eu/rasff-window/backend/public/configuration/"
COUNTRY_URL = "https://webgate.ec.europa.eu/rasff-window/backend/public/country/list/"
PRODUCT_TYPE_URL = (
    "https://webgate.ec.europa.eu/rasff-window/backend/public/productType/list/en/"
)
SEARCH_API_URL = (
    "https://webgate.ec.europa.eu/rasff-window/backend/public/notification/"
    "search/consolidated/en/"
)
DETAIL_URL_TEMPLATE = (
    "https://webgate.ec.europa.eu/rasff-window/screen/notification/{notification_id}"
)
USER_AGENT = (
    "FoodSafetyWatch/0.1 "
    "(+https://github.com/QinkunAry/CheckChineseFoodSafety)"
)

JsonFetcher = Callable[[str, dict[str, Any] | None], bytes]


class RasffFetchError(RuntimeError):
    pass


def _validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != PUBLIC_HOST:
        raise ValueError("RASFF requests are restricted to the official HTTPS host")
    if not parsed.path.startswith("/rasff-window/backend/public/"):
        raise ValueError("RASFF request URL is outside the public API path")


def fetch_public_json(
    url: str,
    payload: dict[str, Any] | None = None,
    *,
    timeout: int = 90,
) -> bytes:
    _validate_public_url(url)
    curl = shutil.which("curl")
    if not curl:
        raise RasffFetchError("curl is required for RASFF requests")
    command = [
        curl,
        "-L",
        "--fail",
        "--silent",
        "--show-error",
        "--ipv4",
        "--http1.1",
        "--retry",
        "3",
        "--retry-all-errors",
        "--connect-timeout",
        "20",
        "--max-time",
        str(timeout),
        "--user-agent",
        USER_AGENT,
        "--referer",
        SEARCH_PAGE_URL,
        "--header",
        "Accept: application/json",
    ]
    request_body: bytes | None = None
    if payload is not None:
        command.extend(
            [
                "--request",
                "POST",
                "--header",
                "Content-Type: application/json",
                "--data-binary",
                "@-",
            ]
        )
        request_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    command.append(url)
    try:
        result = subprocess.run(
            command,
            input=request_body,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as error:
        detail = error.stderr.decode("utf-8", errors="replace").strip()
        raise RasffFetchError(
            f"RASFF request failed for {url}: {detail or error}"
        ) from error
    if not result.stdout:
        raise RasffFetchError(f"RASFF returned an empty response for {url}")
    return result.stdout


def _json_object(payload: bytes | str, label: str) -> dict[str, Any]:
    text = payload.decode("utf-8-sig") if isinstance(payload, bytes) else payload
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError(f"RASFF {label} response root must be an object")
    return value


def parse_configuration(payload: bytes | str) -> dict[str, str]:
    value = _json_object(payload, "configuration")
    link = value.get("openPortalLink")
    support_email = value.get("supportEmail")
    if not isinstance(link, str) or not isinstance(support_email, str):
        raise ValueError("RASFF configuration lacks portal link or support email")
    parsed = urlparse(link)
    is_data_europa_dataset = (
        parsed.scheme == "https"
        and parsed.netloc == DATA_EUROPA_HOST
        and "restored_rasff" in parsed.path
    )
    is_dg_sante_api_details = (
        parsed.scheme == "https"
        and parsed.netloc == DG_SANTE_DEVELOPER_HOST
        and parsed.path == "/api-details"
        and "api=" in parsed.fragment
    )
    if not (is_data_europa_dataset or is_dg_sante_api_details):
        raise ValueError(
            "RASFF configuration portal link is not an official dataset or "
            "DG SANTE API-details URL"
        )
    return {"openPortalLink": link, "supportEmail": support_email}


def parse_country_catalog(payload: bytes | str) -> dict[str, int]:
    value = _json_object(payload, "country catalog")
    countries = value.get("countries")
    if not isinstance(countries, list):
        raise ValueError("RASFF country catalog does not contain countries")
    result: dict[str, int] = {}
    for index, country in enumerate(countries):
        if not isinstance(country, dict):
            raise ValueError(f"RASFF country item {index} is not an object")
        code = country.get("alpha2Code")
        country_id = country.get("id")
        if isinstance(code, str) and isinstance(country_id, int):
            result[code.upper()] = country_id
    if "CN" not in result or "IN" not in result:
        raise ValueError("RASFF country catalog lacks China or India control IDs")
    return result


def parse_product_type_catalog(payload: bytes | str) -> dict[str, int]:
    value = _json_object(payload, "product type catalog")
    product_types = value.get("notificationTypes")
    if not isinstance(product_types, list):
        raise ValueError("RASFF product type catalog lacks notificationTypes")
    result: dict[str, int] = {}
    for index, product_type in enumerate(product_types):
        if not isinstance(product_type, dict):
            raise ValueError(f"RASFF product type item {index} is not an object")
        description = product_type.get("description")
        type_id = product_type.get("id")
        if isinstance(description, str) and isinstance(type_id, int):
            result[description.casefold()] = type_id
    if "food" not in result:
        raise ValueError("RASFF product type catalog lacks human-food ID")
    return result


def build_search_payload(
    *,
    origin_country_id: int,
    food_type_id: int,
    items_per_page: int = 10,
    page_number: int = 1,
) -> dict[str, Any]:
    if origin_country_id < 1 or food_type_id < 1:
        raise ValueError("RASFF filter IDs must be positive integers")
    if not 1 <= items_per_page <= 100:
        raise ValueError("RASFF items_per_page must be between 1 and 100")
    if page_number < 1:
        raise ValueError("RASFF page_number must be at least 1")
    return {
        "parameters": {
            "pageNumber": page_number,
            "itemsPerPage": items_per_page,
        },
        "notificationReference": None,
        "subject": None,
        "notifyingCountry": None,
        "originCountry": [origin_country_id],
        "distributionCountry": None,
        "notificationType": [food_type_id],
        "notificationStatus": None,
        "notificationClassification": None,
        "notificationBasis": None,
        "productCategory": None,
        "actionTaken": None,
        "hazardCategory": None,
        "riskDecision": None,
    }


def _required_mapping(
    notification: dict[str, Any], field: str, index: int
) -> dict[str, Any]:
    value = notification.get(field)
    if not isinstance(value, dict):
        raise ValueError(f"RASFF notification {index} lacks {field}")
    return value


def parse_search_page(
    payload: bytes | str,
) -> tuple[int, int, list[dict[str, Any]]]:
    value = _json_object(payload, "search")
    notifications = value.get("notifications")
    total = value.get("totalElements")
    total_pages = value.get("totalPages")
    if not isinstance(notifications, list):
        raise ValueError("RASFF search response lacks notifications")
    if not isinstance(total, int) or total < 0:
        raise ValueError("RASFF search response has no valid totalElements")
    if not isinstance(total_pages, int) or total_pages < 0:
        raise ValueError("RASFF search response has no valid totalPages")
    parsed: list[dict[str, Any]] = []
    for index, notification in enumerate(notifications):
        if not isinstance(notification, dict):
            raise ValueError(f"RASFF notification {index} is not an object")
        for field in ("notifId", "reference", "ecValidationDate", "subject"):
            item = notification.get(field)
            if field == "notifId":
                valid = isinstance(item, int) and item > 0
            else:
                valid = isinstance(item, str) and bool(item.strip())
            if not valid:
                raise ValueError(f"RASFF notification {index} lacks valid {field}")
        for field in (
            "notifyingCountry",
            "productCategory",
            "productType",
            "notificationClassification",
            "riskDecision",
        ):
            mapping = _required_mapping(notification, field, index)
            if not isinstance(mapping.get("description") or mapping.get("organizationName"), str):
                raise ValueError(f"RASFF notification {index} has invalid {field}")
        origins = notification.get("originCountries")
        if not isinstance(origins, list) or not origins:
            raise ValueError(f"RASFF notification {index} lacks originCountries")
        if any(
            not isinstance(origin, dict)
            or not isinstance(origin.get("isoCode"), str)
            for origin in origins
        ):
            raise ValueError(f"RASFF notification {index} has invalid originCountries")
        parsed.append(notification)
    return total, total_pages, parsed


def parse_search_response(payload: bytes | str) -> tuple[int, list[dict[str, Any]]]:
    total, _, notifications = parse_search_page(payload)
    return total, notifications


def is_china_food_notification(notification: dict[str, Any]) -> bool:
    product_type = notification.get("productType") or {}
    origins = notification.get("originCountries") or []
    return (
        str(product_type.get("description") or "").casefold() == "food"
        and any(
            isinstance(origin, dict)
            and str(origin.get("isoCode") or "").upper() == "CN"
            for origin in origins
        )
    )


def normalize_event_date(value: str) -> str:
    return datetime.strptime(value.strip(), "%d-%m-%Y %H:%M:%S").date().isoformat()


def notification_url(notification_id: int) -> str:
    if not isinstance(notification_id, int) or notification_id < 1:
        raise ValueError("RASFF notification ID must be a positive integer")
    return DETAIL_URL_TEMPLATE.format(notification_id=notification_id)


def normalize_notification(
    notification: dict[str, Any],
    *,
    retrieved_at: str | None = None,
) -> dict[str, Any] | None:
    if not is_china_food_notification(notification):
        return None
    reference = str(notification["reference"]).strip()
    subject = str(notification["subject"]).strip()
    category = str(notification["productCategory"]["description"]).strip()
    notification_id = notification["notifId"]
    return {
        "id": stable_id(SOURCE_ID, reference),
        "source_id": SOURCE_ID,
        "source_record_id": reference,
        "authority": AUTHORITY,
        "authority_region": AUTHORITY_REGION,
        "action_type": "rasff_notification",
        "event_date": normalize_event_date(notification["ecValidationDate"]),
        "origin_country": "CN",
        "regulatory_scope": "origin_based",
        "producer_name": "",
        "producer_location": "",
        "product_code": "",
        "product_category": category,
        # The public consolidated search exposes a notification subject rather
        # than a separate product-name field. Keep it verbatim and document this
        # limitation instead of heuristically deleting hazard wording.
        "product_name": subject,
        "reasons": [subject],
        "hazard_tags": classify_reasons([subject]),
        "source_url": notification_url(notification_id),
        "retrieved_at": retrieved_at or datetime.now(timezone.utc).isoformat(),
    }


def build_rasff_probe_report(
    *,
    schema: dict[str, Any],
    fetcher: JsonFetcher = fetch_public_json,
    min_china_food_records: int = 1_000,
    sample_size: int = 10,
) -> dict[str, Any]:
    if min_china_food_records < 0 or not 2 <= sample_size <= 100:
        raise ValueError("RASFF probe thresholds are invalid")
    generated_at = datetime.now(timezone.utc).isoformat()
    base: dict[str, Any] = {
        "generated_at": generated_at,
        "source_id": SOURCE_ID,
        "dataset_url": DATASET_URL,
        "search_page_url": SEARCH_PAGE_URL,
        "search_api_url": SEARCH_API_URL,
        "minimum_china_food_records": min_china_food_records,
        "sample_size": sample_size,
    }
    try:
        configuration = parse_configuration(fetcher(CONFIG_URL, None))
        countries = parse_country_catalog(fetcher(COUNTRY_URL, None))
        product_types = parse_product_type_catalog(fetcher(PRODUCT_TYPE_URL, None))
        food_type_id = product_types["food"]
        china_total, china_notifications = parse_search_response(
            fetcher(
                SEARCH_API_URL,
                build_search_payload(
                    origin_country_id=countries["CN"],
                    food_type_id=food_type_id,
                    items_per_page=sample_size,
                ),
            )
        )
        india_total, india_notifications = parse_search_response(
            fetcher(
                SEARCH_API_URL,
                build_search_payload(
                    origin_country_id=countries["IN"],
                    food_type_id=food_type_id,
                    items_per_page=2,
                ),
            )
        )
    except Exception as error:
        return {
            **base,
            "status": "failed",
            "blocking_errors": [
                f"RASFF fetch/parse failed: {type(error).__name__}: {error}"
            ],
        }

    blocking_errors: list[str] = []
    if china_total < min_china_food_records:
        blocking_errors.append(
            f"China-origin food count {china_total} below minimum "
            f"{min_china_food_records}"
        )
    if len(china_notifications) < 2:
        blocking_errors.append("RASFF China sample returned fewer than two records")
    invalid_china_count = sum(
        not is_china_food_notification(item) for item in china_notifications
    )
    if invalid_china_count:
        blocking_errors.append(
            f"China food filter returned {invalid_china_count} out-of-scope records"
        )
    invalid_control_count = sum(
        is_china_food_notification(item)
        or str((item.get("productType") or {}).get("description") or "").casefold()
        != "food"
        for item in india_notifications
    )
    if not india_notifications:
        blocking_errors.append("RASFF non-China control returned no records")
    elif invalid_control_count:
        blocking_errors.append(
            f"RASFF non-China control returned {invalid_control_count} invalid records"
        )

    normalized: list[dict[str, Any]] = []
    control_emitted_count = 0
    try:
        normalized = [
            record
            for record in (
                normalize_notification(item, retrieved_at=generated_at)
                for item in china_notifications
            )
            if record is not None
        ]
        control_emitted_count = sum(
            normalize_notification(item, retrieved_at=generated_at) is not None
            for item in india_notifications
        )
    except Exception as error:
        blocking_errors.append(
            f"RASFF normalization failed: {type(error).__name__}: {error}"
        )
    if control_emitted_count:
        blocking_errors.append(
            f"non-China control emitted {control_emitted_count} normalized records"
        )
    quality = build_quality_report(
        normalized,
        schema,
        source_id=SOURCE_ID,
        min_records=2,
    )
    blocking_errors.extend(quality["blocking_errors"])
    return {
        **base,
        "status": "failed" if blocking_errors else "passed",
        "configuration_portal_link": configuration["openPortalLink"],
        "country_catalog_ids": {"CN": countries["CN"], "IN": countries["IN"]},
        "food_product_type_id": food_type_id,
        "china_food_total": china_total,
        "china_sample_count": len(china_notifications),
        "normalized_sample_count": len(normalized),
        "india_food_total": india_total,
        "non_china_control_count": len(india_notifications),
        "non_china_control_emitted_count": control_emitted_count,
        "schema_error_count": quality["schema_error_count"],
        "schema_error_samples": quality["schema_error_samples"],
        "duplicate_id_count": quality["duplicate_id_count"],
        "event_date_min": quality["event_date_min"],
        "event_date_max": quality["event_date_max"],
        "product_categories": quality["product_categories"],
        "hazard_tags": quality["hazard_tags"],
        "china_samples": normalized[:5],
        "blocking_errors": blocking_errors,
    }
