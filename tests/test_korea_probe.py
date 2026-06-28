from __future__ import annotations

import json
import subprocess
import unittest
from unittest.mock import patch

from food_safety_watch.korea_probe import (
    build_korea_probe_report,
    detail_url,
    fetch_probe_recall_records,
    fetch_recall_list,
    has_china_origin_evidence,
    inspect_recall_detail,
    parse_recall_list,
    select_probe_records,
)


CHINA_ID = "3000227626"
VIETNAM_ID = "3000227684"
DOMESTIC_ID = "3000227851"
CHINA_URL = detail_url(CHINA_ID)
VIETNAM_URL = detail_url(VIETNAM_ID)
DOMESTIC_URL = detail_url(DOMESTIC_ID)


def record(record_id: str, product: str, date: str = "2026.06.19") -> dict[str, str]:
    return {
        "rtrvldsuse_seq": record_id,
        "prdtnm": product,
        "rtrvlprvns": "금속성이물 기준 규격 부적합",
        "hmpgpblict_prcsdtm": date,
        "food_type_nm": "가공식품",
        "mnf_natncd": "",
        "incmfood_prdtcd": "",
        "prdlst_report_ledg_no": "",
    }


def list_payload() -> bytes:
    return json.dumps(
        {
            "total_cnt": 3,
            "list": [
                record(DOMESTIC_ID, "자숙홍합살", "2026.06.26"),
                record(VIETNAM_ID, "고춧가루(베트남산)", "2026.06.22"),
                record(CHINA_ID, "고춧가루(중국산)"),
            ],
        },
        ensure_ascii=False,
    ).encode()


def detail_page(
    product: str,
    date: str = "2026.06.19",
    reason: str = "금속성이물(쇳가루) 기준 규격 부적합",
) -> bytes:
    return f"""
    <div class="issue-head">
      <h1>제품명 : {product}</h1><span class="meta">{date}</span>
    </div>
    <dl>
      <dt>회수사유</dt><dd>{reason}</dd>
      <dt>회수영업자</dt><dd>예시 식품</dd>
      <dt>영업자주소</dt><dd>대한민국 예시 주소</dd>
      <dt>등록일</dt><dd>{date}</dd>
      <dt>식품분류</dt><dd>가공식품</dd>
    </dl>
    """.encode()


class KoreaProbeTests(unittest.TestCase):
    def test_list_fetch_uses_retrying_ipv4_curl_request(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=b'{"total_cnt":0,"list":[]}',
            stderr=b"",
        )
        with (
            patch("food_safety_watch.korea_probe.shutil.which", return_value="curl"),
            patch(
                "food_safety_watch.korea_probe.subprocess.run",
                return_value=completed,
            ) as run,
        ):
            payload = fetch_recall_list(show_count=12, search_keyword="중국산")
        self.assertEqual(payload, completed.stdout)
        command = run.call_args.args[0]
        self.assertIn("--ipv4", command)
        self.assertIn("--http1.1", command)
        self.assertIn("--retry-all-errors", command)
        self.assertIn("show_cnt=12", command)
        self.assertIn("search_keyword=중국산", command)

    def test_live_discovery_merges_latest_and_china_search(self) -> None:
        latest = json.dumps(
            {
                "total_cnt": 359,
                "list": [
                    record(DOMESTIC_ID, "자숙홍합살"),
                    record(VIETNAM_ID, "고춧가루(베트남산)"),
                ],
            },
            ensure_ascii=False,
        ).encode()
        china = json.dumps(
            {"total_cnt": 1, "list": [record(CHINA_ID, "고춧가루(중국산)")]},
            ensure_ascii=False,
        ).encode()

        def fetch(**kwargs: object) -> bytes:
            return china if kwargs.get("search_keyword") == "중국산" else latest

        with patch("food_safety_watch.korea_probe.fetch_recall_list", side_effect=fetch):
            total, records, diagnostics = fetch_probe_recall_records()
        self.assertEqual(total, 359)
        self.assertEqual(len(records), 3)
        self.assertEqual(diagnostics["china_search_total"], 1)
        self.assertEqual(
            [value["rtrvldsuse_seq"] for value in records],
            [DOMESTIC_ID, VIETNAM_ID, CHINA_ID],
        )

    def test_origin_evidence_requires_explicit_product_of_china_phrase(self) -> None:
        self.assertTrue(has_china_origin_evidence("고춧가루(중국산)"))
        self.assertTrue(has_china_origin_evidence("원산지: 중국"))
        self.assertFalse(has_china_origin_evidence("중국식 고춧가루"))
        self.assertFalse(has_china_origin_evidence("중국 업체 제품"))

    def test_parse_recall_list_validates_id_and_product(self) -> None:
        total, records = parse_recall_list(list_payload())
        self.assertEqual(total, 3)
        self.assertEqual(len(records), 3)
        self.assertEqual(records[-1]["rtrvldsuse_seq"], CHINA_ID)

    def test_select_probe_records_combines_latest_and_origin_mentions(self) -> None:
        _, records = parse_recall_list(list_payload())
        selected = select_probe_records(records, limit=1, origin_mention_limit=2)
        self.assertEqual(
            [value["rtrvldsuse_seq"] for value in selected],
            [DOMESTIC_ID, CHINA_ID, VIETNAM_ID],
        )

    def test_detail_parser_extracts_required_fields_and_origin(self) -> None:
        detail = inspect_recall_detail(detail_page("고춧가루(중국산)"), CHINA_URL)
        self.assertEqual(detail.source_record_id, CHINA_ID)
        self.assertEqual(detail.product_name, "고춧가루(중국산)")
        self.assertEqual(detail.event_date, "2026-06-19")
        self.assertEqual(detail.food_category, "가공식품")
        self.assertTrue(detail.china_origin_evidence)

    def test_detail_parser_rejects_non_official_url(self) -> None:
        with self.assertRaisesRegex(ValueError, "official HTTPS host"):
            inspect_recall_detail(
                detail_page("고춧가루(중국산)"),
                f"https://example.com/layer/suspensionDetail.do?search_keyword={CHINA_ID}",
            )

    def test_reason_text_alone_cannot_establish_china_origin(self) -> None:
        detail = inspect_recall_detail(
            detail_page("고춧가루", reason="중국산으로 잘못 표시"),
            DOMESTIC_URL,
        )
        self.assertFalse(detail.china_origin_evidence)

    def test_probe_report_preserves_china_and_non_china_evidence(self) -> None:
        payloads = {
            DOMESTIC_URL: detail_page("자숙홍합살", "2026.06.26"),
            VIETNAM_URL: detail_page("고춧가루(베트남산)", "2026.06.22"),
            CHINA_URL: detail_page("고춧가루(중국산)"),
        }
        report = build_korea_probe_report(
            limit=1,
            origin_mention_limit=2,
            list_payload=list_payload(),
            detail_fetcher=payloads.__getitem__,
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["portal_total_count"], 3)
        self.assertEqual(report["portal_explicit_origin_mention_count"], 2)
        self.assertEqual(report["portal_china_origin_product_count"], 1)
        self.assertEqual(report["china_origin_evidence_page_count"], 1)
        self.assertEqual(report["sampled_record_count"], 3)
        self.assertEqual(report["portal_manufacturing_country_field_count"], 0)

    def test_probe_can_enforce_minimum_china_coverage(self) -> None:
        payload = json.dumps(
            {"total_cnt": 1, "list": [record(DOMESTIC_ID, "자숙홍합살")]},
            ensure_ascii=False,
        ).encode()
        report = build_korea_probe_report(
            limit=1,
            origin_mention_limit=0,
            min_china_records=1,
            list_payload=payload,
            detail_fetcher=lambda _: detail_page("자숙홍합살"),
        )
        self.assertEqual(report["status"], "failed")
        self.assertIn(
            "China-origin evidence pages 0 below minimum 1",
            report["blocking_errors"],
        )

    def test_probe_report_fails_closed_on_detail_drift(self) -> None:
        report = build_korea_probe_report(
            limit=1,
            origin_mention_limit=0,
            list_payload=list_payload(),
            detail_fetcher=lambda _: b"<h1>missing fields</h1>",
        )
        self.assertEqual(report["status"], "failed")
        self.assertIn("detail fetch/parse failed", report["blocking_errors"][0])


if __name__ == "__main__":
    unittest.main()
