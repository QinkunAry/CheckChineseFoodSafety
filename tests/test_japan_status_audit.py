from __future__ import annotations

import unittest

from food_safety_watch.japan_status_audit import audit_japan_records


URL = (
    "https://i2fas.mhlw.go.jp/faspub/_link.do?"
    "i=IO_S020502&p=RCL202601519"
)


def record() -> dict[str, object]:
    return {
        "id": "d8439896d81621df96586f7e95180567f37d5b9711dfa64400125c6214566ee8",
        "source_id": "jp_caa_recalls",
        "source_record_id": "RCL202601519",
        "authority": "Ministry of Health, Labour and Welfare, Japan",
        "authority_region": "JP",
        "action_type": "recall",
        "event_date": "2026-06-12",
        "origin_country": "CN",
        "producer_name": "",
        "producer_location": "",
        "product_code": "",
        "product_category": "vegetables",
        "product_name": "とんぶり瓶詰（中国産）",
        "reasons": [
            "食品衛生法違反のおそれ",
            "【回収理由の詳細】 一部商品で異臭が発生したことが判明し、調査の結果、芽胞菌（クロストリジウム属菌）が検出された",
        ],
        "hazard_tags": ["microbiological"],
        "source_url": URL,
        "retrieved_at": "2026-07-05T00:00:00+00:00",
    }


def detail(*, product: str = "とんぶり瓶詰（中国産）", origin: bool = True) -> bytes:
    evidence = product if origin else "とんぶり瓶詰"
    return f"""
    <input type="hidden" name="_rcl_no_str" value="RCL202601519" class="TEXT"/>
    <input type="hidden" name="_rcl_product_str" value="{evidence}" class="TEXT"/>
    <input type="hidden" name="_rcl_date_str" value="2026-06-12" class="DATE"/>
    <input type="hidden" name="_rcl_release_date_str" value="2026-06-26" class="DATE"/>
    <input type="hidden" name="_rcl_rsn_type_str" value="食品衛生法違反のおそれ" class="TEXT"/>
    <input type="hidden" name="_rcl_rsn_memo_str" value="【回収理由の詳細】 一部商品で異臭が発生したことが判明し、調査の結果、芽胞菌（クロストリジウム属菌）が検出された" class="TEXT"/>
    """.encode()


class JapanStatusAuditTests(unittest.TestCase):
    def test_unchanged_mhlw_detail_passes(self) -> None:
        report = audit_japan_records([record()], fetcher=lambda _: detail())
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["audited_record_count"], 1)
        self.assertEqual(report["changed_record_count"], 0)

    def test_product_change_requires_action(self) -> None:
        report = audit_japan_records(
            [record()], fetcher=lambda _: detail(product="とんぶり瓶詰250g（中国産）")
        )
        self.assertEqual(report["status"], "action_required")
        self.assertEqual(report["change_samples"][0]["changes"][0]["field"], "product_name")

    def test_origin_evidence_disappearance_requires_action(self) -> None:
        report = audit_japan_records([record()], fetcher=lambda _: detail(origin=False))
        self.assertEqual(report["status"], "action_required")
        self.assertEqual(
            report["change_samples"][0]["changes"][0]["field"], "origin_country"
        )

    def test_fetch_failure_is_failed(self) -> None:
        def fail(_: str) -> bytes:
            raise TimeoutError("official host timed out")

        report = audit_japan_records([record()], fetcher=fail)
        self.assertEqual(report["status"], "failed")
        self.assertIn("TimeoutError", report["blocking_errors"][0])

    def test_invalid_published_source_url_fails_before_fetch(self) -> None:
        value = record()
        value["source_url"] = "https://example.com/not-official"
        report = audit_japan_records(
            [value], fetcher=lambda _: (_ for _ in ()).throw(AssertionError("no fetch"))
        )
        self.assertEqual(report["status"], "failed")
        self.assertIn("URL/reference mismatch", report["blocking_errors"][0])

    def test_empty_release_passes_but_over_limit_fails_closed(self) -> None:
        empty = audit_japan_records([])
        self.assertEqual(empty["status"], "passed")
        self.assertTrue(empty["warnings"])
        report = audit_japan_records([record(), record()], max_records=1)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["audited_record_count"], 0)


if __name__ == "__main__":
    unittest.main()
