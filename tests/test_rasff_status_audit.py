from __future__ import annotations

import json
import unittest

from food_safety_watch.rasff_detail import detail_api_url, normalize_detail, parse_detail
from food_safety_watch.rasff_status_audit import (
    audit_rasff_records,
    notification_id_from_source_url,
)
from tests.test_rasff_detail import detail_payload


def published_record(payload: bytes) -> dict[str, object]:
    detail = parse_detail(payload)
    record = normalize_detail(
        detail, retrieved_at="2026-07-01T00:00:00+00:00"
    )
    assert record is not None
    return record


class RasffStatusAuditTests(unittest.TestCase):
    def test_unchanged_official_detail_passes(self) -> None:
        payload = detail_payload()
        record = published_record(payload)
        report = audit_rasff_records(
            [record],
            fetcher=lambda url, _body: (
                payload if url == detail_api_url(852931) else b""
            ),
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["audited_record_count"], 1)
        self.assertEqual(report["changed_record_count"], 0)

    def test_active_to_withdrawn_requires_action(self) -> None:
        active_payload = detail_payload()
        withdrawn_payload = detail_payload(status="ec_withdrawn")
        record = published_record(active_payload)
        report = audit_rasff_records(
            [record], fetcher=lambda _url, _body: withdrawn_payload
        )
        self.assertEqual(report["status"], "action_required")
        self.assertEqual(report["changed_record_count"], 1)
        sample = report["change_samples"][0]
        self.assertEqual(sample["previous_record_status"], "active")
        self.assertEqual(sample["current_record_status"], "withdrawn")
        self.assertIn("record_status", sample["changed_fields"])
        self.assertIn("official_notification_status", sample["changed_fields"])

    def test_product_or_hazard_correction_requires_action(self) -> None:
        original = detail_payload()
        changed = json.loads(original)
        changed["product"]["description"] = "Corrected Pepper Powder"
        changed["lastUpdate"] = "01-07-2026 10:00:00"
        report = audit_rasff_records(
            [published_record(original)],
            fetcher=lambda _url, _body: json.dumps(changed).encode(),
        )
        self.assertEqual(report["status"], "action_required")
        fields = report["change_samples"][0]["changed_fields"]
        self.assertIn("product_name", fields)
        self.assertIn("official_last_update", fields)

    def test_invalid_source_or_source_url_fails_closed(self) -> None:
        record = published_record(detail_payload())
        record["source_url"] = "https://example.com/notification/852931"
        report = audit_rasff_records([record], fetcher=lambda _url, _body: b"")
        self.assertEqual(report["status"], "failed")
        self.assertIn("official HTTPS host", report["blocking_errors"][0])

        record = published_record(detail_payload())
        record["source_id"] = "other_source"
        report = audit_rasff_records([record], fetcher=lambda _url, _body: b"")
        self.assertEqual(report["status"], "failed")
        self.assertIn("is not from", report["blocking_errors"][0])

    def test_fetch_failure_is_reported(self) -> None:
        record = published_record(detail_payload())
        report = audit_rasff_records(
            [record],
            fetcher=lambda _url, _body: (_ for _ in ()).throw(
                TimeoutError("timed out")
            ),
        )
        self.assertEqual(report["status"], "failed")
        self.assertIn("timed out", report["blocking_errors"][0])

    def test_empty_and_over_limit_inputs_fail_before_network(self) -> None:
        empty = audit_rasff_records([])
        self.assertEqual(empty["status"], "failed")
        self.assertIn("input is empty", empty["blocking_errors"][0])

        record = published_record(detail_payload())
        over = audit_rasff_records([record, record], max_records=1)
        self.assertEqual(over["status"], "failed")
        self.assertIn("exceeds audit maximum", over["blocking_errors"][0])

    def test_source_url_parser_rejects_query_and_wrong_path(self) -> None:
        self.assertEqual(
            notification_id_from_source_url(
                "https://webgate.ec.europa.eu/rasff-window/screen/notification/852931"
            ),
            852931,
        )
        with self.assertRaisesRegex(ValueError, "unexpected detail path"):
            notification_id_from_source_url(
                "https://webgate.ec.europa.eu/rasff-window/screen/notification/852931?x=1"
            )


if __name__ == "__main__":
    unittest.main()
