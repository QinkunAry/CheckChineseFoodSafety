from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from food_safety_watch.quality import load_schema
from food_safety_watch.rasff_probe import (
    CONFIG_URL,
    COUNTRY_URL,
    PRODUCT_TYPE_URL,
    SEARCH_API_URL,
    build_rasff_probe_report,
    build_search_payload,
    fetch_public_json,
    is_china_food_notification,
    normalize_notification,
    parse_configuration,
    parse_country_catalog,
    parse_search_response,
)


SCHEMA = load_schema(Path("schemas/record.schema.json"))


def configuration_payload() -> bytes:
    return json.dumps(
        {
            "supportEmail": "SANTE-RASFF-AAC-FF-SUPPORT@ec.europa.eu",
            "openPortalLink": (
                "https://data.europa.eu/data/datasets/restored_rasff~~1?locale=en"
            ),
        }
    ).encode()


def developer_portal_configuration_payload() -> bytes:
    return json.dumps(
        {
            "supportEmail": "SANTE-RASFF-AAC-FF-SUPPORT@ec.europa.eu",
            "openPortalLink": (
                "https://developer.datalake.sante.service.ec.europa.eu/"
                "api-details#api=2955fdc1-9da2-4927-977f-40dc50db1128"
                "&operation=cc6aab62-bd15-4904-b20d-54551ccb9468"
            ),
        }
    ).encode()


def country_payload() -> bytes:
    return json.dumps(
        {
            "countries": [
                {"id": 5075, "englishShortName": "China", "alpha2Code": "CN"},
                {"id": 5118, "englishShortName": "India", "alpha2Code": "IN"},
            ]
        }
    ).encode()


def product_type_payload() -> bytes:
    return json.dumps(
        {
            "notificationTypes": [
                {"id": 282, "description": "feed"},
                {"id": 283, "description": "food"},
            ]
        }
    ).encode()


def notification(
    notification_id: int,
    reference: str,
    *,
    origin: str = "CN",
    product_type: str = "food",
    product_type_id: int = 283,
) -> dict[str, object]:
    return {
        "notifId": notification_id,
        "ecValidationDate": "24-06-2026 12:36:41",
        "reference": reference,
        "notifyingCountry": {
            "organizationName": "Netherlands",
            "isoCode": "NL",
        },
        "subject": "anthraquinone in pepper powder from China",
        "productCategory": {"id": 18450, "description": "herbs and spices"},
        "productType": {"id": product_type_id, "description": product_type},
        "notificationClassification": {
            "id": 306,
            "description": "alert notification",
        },
        "riskDecision": {"id": 18761, "description": "serious"},
        "published": False,
        "originCountries": [
            {
                "organizationName": "China" if origin == "CN" else "India",
                "isoCode": origin,
            }
        ],
    }


def search_payload(
    records: list[dict[str, object]], total: int = 1_211
) -> bytes:
    return json.dumps(
        {"notifications": records, "totalPages": 122, "totalElements": total}
    ).encode()


class RasffProbeTests(unittest.TestCase):
    def test_fetch_uses_json_post_body_and_retrying_curl(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=b'{"ok":true}', stderr=b""
        )
        request = build_search_payload(
            origin_country_id=5075, food_type_id=283, items_per_page=10
        )
        with (
            patch("food_safety_watch.rasff_probe.shutil.which", return_value="curl"),
            patch(
                "food_safety_watch.rasff_probe.subprocess.run",
                return_value=completed,
            ) as run,
        ):
            result = fetch_public_json(SEARCH_API_URL, request)
        self.assertEqual(result, completed.stdout)
        command = run.call_args.args[0]
        self.assertIn("--ipv4", command)
        self.assertIn("--retry-all-errors", command)
        self.assertIn("@-", command)
        sent = json.loads(run.call_args.kwargs["input"])
        self.assertEqual(sent["originCountry"], [5075])
        self.assertEqual(sent["notificationType"], [283])

    def test_fetch_rejects_non_official_or_non_public_url(self) -> None:
        with self.assertRaisesRegex(ValueError, "official HTTPS host"):
            fetch_public_json("https://example.com/rasff", None)
        with self.assertRaisesRegex(ValueError, "outside the public API"):
            fetch_public_json(
                "https://webgate.ec.europa.eu/rasff-window/private/data", None
            )

    def test_catalog_ids_are_read_from_official_payload(self) -> None:
        self.assertEqual(parse_country_catalog(country_payload())["CN"], 5075)
        missing = json.dumps(
            {"countries": [{"id": 5118, "alpha2Code": "IN"}]}
        ).encode()
        with self.assertRaisesRegex(ValueError, "lacks China or India"):
            parse_country_catalog(missing)

    def test_configuration_accepts_dataset_and_developer_portal_links(self) -> None:
        self.assertIn(
            "restored_rasff",
            parse_configuration(configuration_payload())["openPortalLink"],
        )
        self.assertIn(
            "developer.datalake.sante.service.ec.europa.eu",
            parse_configuration(developer_portal_configuration_payload())[
                "openPortalLink"
            ],
        )
        invalid = json.dumps(
            {
                "supportEmail": "SANTE-RASFF-AAC-FF-SUPPORT@ec.europa.eu",
                "openPortalLink": "https://example.com/api-details#api=1",
            }
        ).encode()
        with self.assertRaisesRegex(ValueError, "not an official"):
            parse_configuration(invalid)

    def test_search_payload_applies_origin_and_human_food_filters(self) -> None:
        payload = build_search_payload(
            origin_country_id=5075, food_type_id=283, items_per_page=25
        )
        self.assertEqual(payload["originCountry"], [5075])
        self.assertEqual(payload["notificationType"], [283])
        self.assertEqual(payload["parameters"]["itemsPerPage"], 25)

    def test_parser_requires_critical_origin_and_product_fields(self) -> None:
        total, records = parse_search_response(
            search_payload([notification(853498, "2026.5655")])
        )
        self.assertEqual(total, 1_211)
        self.assertEqual(records[0]["reference"], "2026.5655")
        invalid = notification(853498, "2026.5655")
        invalid["originCountries"] = []
        with self.assertRaisesRegex(ValueError, "lacks originCountries"):
            parse_search_response(search_payload([invalid]))

    def test_normalization_requires_explicit_china_and_food(self) -> None:
        china = notification(853498, "2026.5655")
        india = notification(853499, "2026.5656", origin="IN")
        feed = notification(
            853500,
            "2026.5657",
            product_type="feed",
            product_type_id=282,
        )
        self.assertTrue(is_china_food_notification(china))
        record = normalize_notification(
            china, retrieved_at="2026-06-30T00:00:00+00:00"
        )
        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record["event_date"], "2026-06-24")
        self.assertEqual(record["origin_country"], "CN")
        self.assertEqual(record["action_type"], "rasff_notification")
        self.assertIsNone(normalize_notification(india))
        self.assertIsNone(normalize_notification(feed))

    def test_probe_validates_catalog_filters_control_and_schema(self) -> None:
        china = [
            notification(853498, "2026.5655"),
            notification(853889, "2026.5625"),
        ]
        india = [notification(900001, "2026.6001", origin="IN")]

        def fetch(url: str, request: dict[str, object] | None) -> bytes:
            if url == CONFIG_URL:
                return configuration_payload()
            if url == COUNTRY_URL:
                return country_payload()
            if url == PRODUCT_TYPE_URL:
                return product_type_payload()
            if url == SEARCH_API_URL and request:
                if request["originCountry"] == [5075]:
                    return search_payload(china, total=1_211)
                if request["originCountry"] == [5118]:
                    return search_payload(india, total=2_083)
            raise AssertionError((url, request))

        report = build_rasff_probe_report(schema=SCHEMA, fetcher=fetch, sample_size=2)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["china_food_total"], 1_211)
        self.assertEqual(report["normalized_sample_count"], 2)
        self.assertEqual(report["non_china_control_emitted_count"], 0)
        self.assertEqual(report["schema_error_count"], 0)

    def test_probe_fails_closed_on_filter_drift(self) -> None:
        china_with_feed = [
            notification(853498, "2026.5655"),
            notification(
                853500,
                "2026.5657",
                product_type="feed",
                product_type_id=282,
            ),
        ]
        india = [notification(900001, "2026.6001", origin="IN")]

        def fetch(url: str, request: dict[str, object] | None) -> bytes:
            payloads = {
                CONFIG_URL: configuration_payload(),
                COUNTRY_URL: country_payload(),
                PRODUCT_TYPE_URL: product_type_payload(),
            }
            if url in payloads:
                return payloads[url]
            assert request is not None
            records = (
                china_with_feed if request["originCountry"] == [5075] else india
            )
            return search_payload(records)

        report = build_rasff_probe_report(schema=SCHEMA, fetcher=fetch, sample_size=2)
        self.assertEqual(report["status"], "failed")
        self.assertTrue(
            any("out-of-scope" in error for error in report["blocking_errors"])
        )

    def test_probe_reports_normalization_drift_instead_of_crashing(self) -> None:
        china = [
            notification(853498, "2026.5655"),
            notification(853889, "2026.5625"),
        ]
        china[0]["ecValidationDate"] = "unexpected date"
        india = [notification(900001, "2026.6001", origin="IN")]

        def fetch(url: str, request: dict[str, object] | None) -> bytes:
            payloads = {
                CONFIG_URL: configuration_payload(),
                COUNTRY_URL: country_payload(),
                PRODUCT_TYPE_URL: product_type_payload(),
            }
            if url in payloads:
                return payloads[url]
            assert request is not None
            records = china if request["originCountry"] == [5075] else india
            return search_payload(records)

        report = build_rasff_probe_report(schema=SCHEMA, fetcher=fetch, sample_size=2)
        self.assertEqual(report["status"], "failed")
        self.assertTrue(
            any("normalization failed" in error for error in report["blocking_errors"])
        )

    def test_probe_reports_network_failure(self) -> None:
        def fail(_: str, __: dict[str, object] | None) -> bytes:
            raise TimeoutError("official endpoint timed out")

        report = build_rasff_probe_report(schema=SCHEMA, fetcher=fail, sample_size=2)
        self.assertEqual(report["status"], "failed")
        self.assertIn("fetch/parse failed", report["blocking_errors"][0])
        self.assertIn("timed out", report["blocking_errors"][0])


if __name__ == "__main__":
    unittest.main()
