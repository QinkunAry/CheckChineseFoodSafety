from __future__ import annotations

import unittest

from food_safety_watch.japan_probe import CAA_FOOD_URL
from food_safety_watch.japan_smoke import (
    build_japan_smoke_report,
    caa_rcl_from_detail_url,
    mhlw_detail_url,
)


CHINA_CAA_URL = "https://www.recall.caa.go.jp/result/detail.php?rcl=00000035456&screenkbn=01"
OTHER_CAA_URL = "https://www.recall.caa.go.jp/result/detail.php?rcl=00000035460&screenkbn=01"
SECOND_CHINA_CAA_URL = "https://www.recall.caa.go.jp/result/detail.php?rcl=00000035471&screenkbn=01"
CHINA_MHLW_URL = "https://i2fas.mhlw.go.jp/faspub/_link.do?i=IO_S020502&p=RCL202601495"
OTHER_MHLW_URL = "https://i2fas.mhlw.go.jp/faspub/_link.do?i=IO_S020502&p=RCL202601499"
SECOND_CHINA_MHLW_URL = "https://i2fas.mhlw.go.jp/faspub/_link.do?i=IO_S020502&p=RCL202601519"


def list_page(total: int = 320) -> bytes:
    return f"""
    <p>{total}件中　1-15件を表示中</p>
    <tr>
      <td><p><a href="/result/detail.php?rcl=00000035460&screenkbn=01">普通の商品 - 回収</a></p></td>
      <td><span class="result_list_post_date">2026/06/24</span></td>
      <td><span class="result_list_start_date">2026/06/22</span></td>
    </tr>
    """.encode()


def caa_detail(*, china: bool, mhlw_id: str) -> bytes:
    product = "中国産うなぎ長焼" if china else "国内製造うどん"
    return f"""
    <h3>{product} - 返金／回収</h3>
    <input type="hidden" name="_rcl_product_str" value="{product}" class="TEXT"/>
    <input type="hidden" name="_rcl_rsn_type_str" value="食品表示法違反" class="TEXT"/>
    <a href="https://i2fas.mhlw.go.jp/faspub/_link.do?i=IO_S020502&amp;p={mhlw_id}">参照情報</a>
    """.encode()


def mhlw_detail(*, china: bool, rcl_id: str) -> bytes:
    product = "中国産うなぎ長焼" if china else "国内製造うどん"
    return f"""
    <input type="hidden" name="_rcl_no_str" value="{rcl_id}" class="TEXT"/>
    <input type="hidden" name="_rcl_product_str" value="{product}" class="TEXT"/>
    <input type="hidden" name="_rcl_rsn_type_str" value="食品表示法違反" class="TEXT"/>
    """.encode()


class JapanSmokeTests(unittest.TestCase):
    def test_caa_detail_url_validation_rejects_non_official_hosts(self) -> None:
        with self.assertRaises(ValueError):
            caa_rcl_from_detail_url("https://example.com/result/detail.php?rcl=1&screenkbn=01")

    def test_caa_detail_url_validation_extracts_rcl(self) -> None:
        self.assertEqual(caa_rcl_from_detail_url(CHINA_CAA_URL), "00000035456")

    def test_mhlw_detail_url_requires_rcl_id(self) -> None:
        self.assertEqual(mhlw_detail_url("RCL202601495"), CHINA_MHLW_URL)
        with self.assertRaises(ValueError):
            mhlw_detail_url("00000035456")

    def test_smoke_report_passes_with_china_origin_and_mhlw_reference(self) -> None:
        payloads = {
            CAA_FOOD_URL: list_page(),
            CHINA_CAA_URL: caa_detail(china=True, mhlw_id="RCL202601495"),
            OTHER_CAA_URL: caa_detail(china=False, mhlw_id="RCL202601499"),
            CHINA_MHLW_URL: mhlw_detail(china=True, rcl_id="RCL202601495"),
            OTHER_MHLW_URL: mhlw_detail(china=False, rcl_id="RCL202601499"),
        }
        report = build_japan_smoke_report(
            urls=[CHINA_CAA_URL, OTHER_CAA_URL],
            min_list_total=100,
            min_china_records=1,
            min_mhlw_references=2,
            fetcher=lambda url: payloads[url],
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["list_total_count"], 320)
        self.assertEqual(report["tested_page_count"], 2)
        self.assertEqual(report["china_origin_evidence_page_count"], 1)
        self.assertEqual(report["mhlw_reference_count"], 2)

    def test_smoke_report_fails_closed_when_china_evidence_is_missing(self) -> None:
        payloads = {
            CAA_FOOD_URL: list_page(),
            OTHER_CAA_URL: caa_detail(china=False, mhlw_id="RCL202601499"),
            OTHER_MHLW_URL: mhlw_detail(china=False, rcl_id="RCL202601499"),
        }
        report = build_japan_smoke_report(
            urls=[OTHER_CAA_URL],
            min_china_records=1,
            fetcher=lambda url: payloads[url],
        )
        self.assertEqual(report["status"], "failed")
        self.assertIn("China-origin evidence pages 0 below minimum 1", report["blocking_errors"])

    def test_smoke_report_supports_two_china_samples_and_non_china_control(self) -> None:
        payloads = {
            CAA_FOOD_URL: list_page(),
            CHINA_CAA_URL: caa_detail(china=True, mhlw_id="RCL202601495"),
            SECOND_CHINA_CAA_URL: caa_detail(china=True, mhlw_id="RCL202601519"),
            OTHER_CAA_URL: caa_detail(china=False, mhlw_id="RCL202601499"),
            CHINA_MHLW_URL: mhlw_detail(china=True, rcl_id="RCL202601495"),
            SECOND_CHINA_MHLW_URL: mhlw_detail(china=True, rcl_id="RCL202601519"),
            OTHER_MHLW_URL: mhlw_detail(china=False, rcl_id="RCL202601499"),
        }
        report = build_japan_smoke_report(
            urls=[CHINA_CAA_URL, SECOND_CHINA_CAA_URL, OTHER_CAA_URL],
            min_china_records=2,
            min_mhlw_references=3,
            fetcher=payloads.__getitem__,
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["tested_page_count"], 3)
        self.assertEqual(report["china_origin_evidence_page_count"], 2)
        self.assertEqual(report["mhlw_reference_count"], 3)

    def test_smoke_report_fails_closed_when_list_count_drops(self) -> None:
        payloads = {
            CAA_FOOD_URL: list_page(total=3),
            CHINA_CAA_URL: caa_detail(china=True, mhlw_id="RCL202601495"),
            CHINA_MHLW_URL: mhlw_detail(china=True, rcl_id="RCL202601495"),
        }
        report = build_japan_smoke_report(
            urls=[CHINA_CAA_URL],
            min_list_total=100,
            fetcher=lambda url: payloads[url],
        )
        self.assertEqual(report["status"], "failed")
        self.assertIn("CAA food list count 3 is below minimum 100", report["blocking_errors"])


if __name__ == "__main__":
    unittest.main()
