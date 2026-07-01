from __future__ import annotations

import json
import unittest
from pathlib import Path

from food_safety_watch.quality import build_quality_report, load_schema
from food_safety_watch.rasff_detail import (
    detail_api_url,
    is_china_food_detail,
    lifecycle_status,
    normalize_detail,
    parse_detail,
)


SCHEMA = load_schema(Path("schemas/record.schema.json"))


def detail_payload(
    *,
    notification_id: int = 852931,
    reference: str = "2026.5575",
    origin: str = "CN",
    product_name: str = "Pepper Powder",
    status: str = "ec_validated",
    with_hazard: bool = True,
) -> bytes:
    hazards = []
    if with_hazard:
        hazards = [
            {
                "id": 30775510,
                "name": "anthraquinone - pesticide residues",
                "analyticalResult": "0,078",
                "unit": "mg/kg - ppm",
                "samplingDate": "08-04-2026 00:00:00",
                "maxPermittedLvl": "0,02 mg/kg - ppm",
                "hazardCategory": {"description": "pesticide residues"},
            }
        ]
    value = {
        "id": notification_id,
        "reference": reference,
        "subject": "anthraquinone in Pepper Powder from China",
        "ecValidationDate": "24-06-2026 12:36:41",
        "lastUpdate": "29-06-2026 09:51:44",
        "notificationClassification": {
            "id": 306,
            "description": "alert notification",
        },
        "productType": {"id": 283, "description": "food"},
        "notificationBasis": {
            "id": 18423,
            "description": "company's own check",
        },
        "product": {
            "id": 30767054,
            "description": product_name,
            "productCategory": {
                "id": 18427,
                "description": "nuts, nut products and seeds",
            },
            "hazards": hazards,
            "measures": [
                {
                    "id": 1,
                    "actionTaken": {"id": 18826, "description": "informing consignor"},
                }
            ],
            "distributionStatus": {
                "id": 219,
                "description": "distribution to other member countries",
            },
        },
        "risk": {"id": 137269, "riskDecision": "serious"},
        "organizationFlags": [
            {
                "organization": {
                    "id": 10070,
                    "description": "China" if origin == "CN" else "India",
                    "code": origin,
                },
                "notificationFlags": [
                    {"notificationId": notification_id, "flagType": "ORIGIN"}
                ],
            }
        ],
        "notificationStatus": status,
        "followups": (
            [
                {
                    "fupNumber": 1,
                    "fupType": {
                        "id": 27676,
                        "description": "withdrawal of original notification",
                    },
                }
            ]
            if status == "ec_withdrawn"
            else []
        ),
    }
    return json.dumps(value).encode()


class RasffDetailTests(unittest.TestCase):
    def test_detail_url_uses_official_public_path(self) -> None:
        self.assertEqual(
            detail_api_url(852931),
            "https://webgate.ec.europa.eu/rasff-window/backend/public/"
            "notification/view/id/852931/en/",
        )
        with self.assertRaisesRegex(ValueError, "positive integer"):
            detail_api_url(0)

    def test_parser_extracts_product_hazard_status_and_origin(self) -> None:
        detail = parse_detail(
            detail_payload(status="ec_withdrawn"),
            expected_id=852931,
            expected_reference="2026.5575",
        )
        self.assertEqual(detail["product_name"], "Pepper Powder")
        self.assertEqual(detail["hazards"][0]["category"], "pesticide residues")
        self.assertEqual(detail["notification_status"], "ec_withdrawn")
        self.assertEqual(detail["origin_codes"], ["CN"])
        self.assertEqual(
            detail["followup_types"], ["withdrawal of original notification"]
        )
        self.assertTrue(is_china_food_detail(detail))

    def test_normalized_detail_uses_product_and_official_hazard(self) -> None:
        detail = parse_detail(detail_payload())
        record = normalize_detail(
            detail, retrieved_at="2026-07-01T00:00:00+00:00"
        )
        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record["product_name"], "Pepper Powder")
        self.assertEqual(record["reasons"], ["anthraquinone - pesticide residues"])
        self.assertEqual(record["hazard_tags"], ["chemical"])
        self.assertEqual(record["official_risk_decision"], "serious")
        self.assertEqual(record["official_notification_status"], "ec_validated")
        self.assertEqual(record["official_followup_types"], [])
        self.assertEqual(record["record_status"], "active")
        quality = build_quality_report(
            [record], SCHEMA, source_id="eu_rasff", min_records=1
        )
        self.assertEqual(quality["status"], "passed")

    def test_no_hazard_uses_subject_but_keeps_real_product_name(self) -> None:
        detail = parse_detail(
            detail_payload(product_name="Vermicelli", with_hazard=False)
        )
        record = normalize_detail(detail)
        assert record is not None
        self.assertEqual(record["product_name"], "Vermicelli")
        self.assertEqual(record["reasons"], [detail["subject"]])
        self.assertEqual(record["official_hazards"], [])

    def test_official_mycotoxin_category_maps_to_chemical(self) -> None:
        value = json.loads(detail_payload())
        value["product"]["hazards"][0]["name"] = "Aflatoxin B1 - mycotoxins"
        value["product"]["hazards"][0]["hazardCategory"]["description"] = (
            "mycotoxins"
        )
        detail = parse_detail(json.dumps(value))
        record = normalize_detail(detail)
        assert record is not None
        self.assertEqual(record["hazard_tags"], ["chemical"])

    def test_non_china_origin_is_not_normalized(self) -> None:
        detail = parse_detail(detail_payload(origin="IN"))
        self.assertFalse(is_china_food_detail(detail))
        self.assertIsNone(normalize_detail(detail))

    def test_lifecycle_state_machine_handles_corrigendum_and_withdrawal(self) -> None:
        active = parse_detail(detail_payload())
        active["followup_types"] = ["corrigendum"]
        self.assertEqual(lifecycle_status(active), "active")

        withdrawn = parse_detail(detail_payload(status="ec_withdrawn"))
        self.assertEqual(lifecycle_status(withdrawn), "withdrawn")

        contradictory = parse_detail(detail_payload())
        contradictory["followup_types"] = ["withdrawal of original notification"]
        self.assertEqual(lifecycle_status(contradictory), "review_required")

        unknown = parse_detail(detail_payload())
        unknown["notification_status"] = "unexpected_status"
        self.assertEqual(lifecycle_status(unknown), "review_required")

    def test_parser_rejects_identity_mismatch_and_missing_origin(self) -> None:
        with self.assertRaisesRegex(ValueError, "ID mismatch"):
            parse_detail(detail_payload(), expected_id=1)
        value = json.loads(detail_payload())
        value["organizationFlags"][0]["notificationFlags"] = []
        with self.assertRaisesRegex(ValueError, "no explicit ORIGIN"):
            parse_detail(json.dumps(value))


if __name__ == "__main__":
    unittest.main()
