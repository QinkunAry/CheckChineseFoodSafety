from __future__ import annotations

import unittest

from food_safety_watch.japan_probe import (
    CAA_FOOD_URL,
    build_japan_probe_report,
    has_china_origin_evidence,
    inspect_caa_detail,
    inspect_mhlw_detail,
    parse_caa_food_list,
    select_probe_items,
)


DETAIL_URL = "https://www.recall.caa.go.jp/result/detail.php?rcl=00000035456&screenkbn=01"
MHLW_URL = "https://i2fas.mhlw.go.jp/faspub/_link.do?i=IO_S020502&p=RCL202601495"


def list_page() -> bytes:
    return f"""
    <p>320件中　1-15件を表示中</p>
    <tr>
      <td><span class="result_list_category category_1">食料品</span></td>
      <td><p><a href="/result/detail.php?rcl=00000035460&screenkbn=01">普通の商品 - 回収</a></p></td>
      <td><span class="result_list_post_date">2026/06/24</span></td>
      <td><span class="result_list_start_date">2026/06/22</span></td>
    </tr>
    <tr>
      <td><span class="result_list_category category_1">食料品</span></td>
      <td><p><a href="/result/detail.php?rcl=00000035456&screenkbn=01">中国産うなぎ - 返金／回収</a></p></td>
      <td><span class="result_list_post_date">2026/06/22</span></td>
      <td><span class="result_list_start_date">2026/06/21</span></td>
    </tr>
    """.encode()


def caa_detail() -> bytes:
    return """
    <div class="detail_title">
      <h3>マルエツ「中国産うなぎ」 - 返金／回収</h3>
      <p>消費期限の誤表示</p>
    </div>
    <span class="detail_cap">対応開始日</span>
    <span class="detail_text">2026年06月21日</span>
    <input type="hidden" name="_rcl_product_str" value="中国産うなぎ長焼" class="TEXT"/>
    <input type="hidden" name="_rcl_info_str" value="商品名：中国産うなぎ長焼" class="TEXT"/>
    <input type="hidden" name="_rcl_rsn_type_str" value="食品表示法違反" class="TEXT"/>
    <input type="hidden" name="_rcl_rsn_memo_str" value="期限表示の印字誤り" class="TEXT"/>
    <a href="https://i2fas.mhlw.go.jp/faspub/_link.do?i=IO_S020502&amp;p=RCL202601495">参照情報</a>
    """.encode()


def mhlw_detail() -> bytes:
    return """
    <input type="hidden" name="_rcl_no_str" value="RCL202601495" class="TEXT"/>
    <input type="hidden" name="_rcl_product_str" value="中国産うなぎ長焼" class="TEXT"/>
    <input type="hidden" name="_rcl_date_str" value="2026-06-21" class="DATE"/>
    <input type="hidden" name="_rcl_info_str" value="商品名：中国産うなぎ長焼" class="TEXT"/>
    <input type="hidden" name="_rcl_rsn_type_str" value="食品表示法違反" class="TEXT"/>
    <input type="hidden" name="_rcl_rsn_memo_str" value="期限表示の印字誤り" class="TEXT"/>
    """.encode()


class JapanProbeTests(unittest.TestCase):
    def test_parse_caa_food_list_extracts_total_and_items(self) -> None:
        total, items = parse_caa_food_list(list_page(), base_url=CAA_FOOD_URL)
        self.assertEqual(total, 320)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[1].rcl, "00000035456")
        self.assertEqual(items[1].title, "中国産うなぎ - 返金／回収")

    def test_select_probe_items_combines_latest_and_china_titles(self) -> None:
        _, items = parse_caa_food_list(list_page(), base_url=CAA_FOOD_URL)
        selected = select_probe_items(items, limit=1, china_mention_limit=1)
        self.assertEqual([item.rcl for item in selected], ["00000035460", "00000035456"])

    def test_china_origin_evidence_is_explicit(self) -> None:
        self.assertTrue(has_china_origin_evidence("商品名：中国産うなぎ"))
        self.assertFalse(has_china_origin_evidence("中華風サラダ"))

    def test_inspect_caa_detail_extracts_mhlw_reference_and_evidence(self) -> None:
        detail = inspect_caa_detail(caa_detail())
        self.assertEqual(detail["mhlw_reference_id"], "RCL202601495")
        self.assertEqual(detail["event_date"], "2026年06月21日")
        self.assertEqual(detail["summary"], "消費期限の誤表示")
        self.assertTrue(detail["china_origin_evidence"])

    def test_inspect_mhlw_detail_extracts_hidden_fields(self) -> None:
        detail = inspect_mhlw_detail(mhlw_detail())
        self.assertEqual(detail["rcl_no"], "RCL202601495")
        self.assertEqual(detail["event_date"], "2026-06-21")
        self.assertEqual(detail["reason_type"], "食品表示法違反")
        self.assertTrue(detail["china_origin_evidence"])

    def test_build_japan_probe_report_fetches_caa_and_mhlw_details(self) -> None:
        payloads = {
            CAA_FOOD_URL: list_page(),
            "https://www.recall.caa.go.jp/result/detail.php?rcl=00000035460&screenkbn=01": caa_detail(),
            DETAIL_URL: caa_detail(),
            MHLW_URL: mhlw_detail(),
        }
        report = build_japan_probe_report(
            limit=1,
            china_mention_limit=1,
            fetcher=lambda url: payloads[url],
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["list_total_count"], 320)
        self.assertEqual(report["sampled_record_count"], 2)
        self.assertEqual(report["china_origin_evidence_page_count"], 2)
        self.assertEqual(report["mhlw_reference_count"], 2)


if __name__ == "__main__":
    unittest.main()
