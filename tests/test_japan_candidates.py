from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from food_safety_watch.japan_candidates import (
    build_candidate_report,
    candidate_japan_caa,
    new_recall_items,
    select_candidate_items,
)
from food_safety_watch.japan_probe import CaaListItem
from food_safety_watch.quality import load_schema


SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "record.schema.json"
CHINA_URL = "https://www.recall.caa.go.jp/result/detail.php?rcl=00000035456&screenkbn=01"
OTHER_URL = "https://www.recall.caa.go.jp/result/detail.php?rcl=00000035460&screenkbn=01"
MHLW_URL = "https://i2fas.mhlw.go.jp/faspub/_link.do?i=IO_S020502&p=RCL202601495"


def item(url: str, title: str = "商品 - 回収") -> CaaListItem:
    rcl = url.split("rcl=", 1)[1].split("&", 1)[0]
    return CaaListItem(
        rcl=rcl,
        title=title,
        url=url,
        post_date="2026/06/22",
        start_date="2026/06/21",
    )


def caa_detail(*, china: bool, mhlw: bool = True) -> bytes:
    product = "中国産うなぎ長焼" if china else "国内製造うどん"
    reference = (
        '<a href="https://i2fas.mhlw.go.jp/faspub/_link.do?'
        'i=IO_S020502&amp;p=RCL202601495">参照情報</a>'
        if mhlw else ""
    )
    return f"""
    <div class="detail_title">
      <h3>{product} - 返金／回収</h3>
      <p>消費期限の誤表示</p>
    </div>
    <span class="detail_cap">商品名</span>
    <span class="detail_text">{product}</span>
    <span class="detail_cap">対応開始日</span>
    <span class="detail_text">2026年06月21日</span>
    {reference}
    """.encode()


def mhlw_detail(*, china: bool = True, rcl: str = "RCL202601495") -> bytes:
    product = "中国産うなぎ長焼" if china else "国内製造うどん"
    return f"""
    <input type="hidden" name="_rcl_no_str" value="{rcl}" class="TEXT"/>
    <input type="hidden" name="_rcl_product_str" value="{product}" class="TEXT"/>
    <input type="hidden" name="_rcl_date_str" value="2026-06-21" class="DATE"/>
    <input type="hidden" name="_rcl_release_date_str" value="2026-06-22" class="DATE"/>
    <input type="hidden" name="_rcl_rsn_type_str" value="食品表示法違反" class="TEXT"/>
    <input type="hidden" name="_rcl_rsn_memo_str" value="期限表示の印字誤り" class="TEXT"/>
    """.encode()


def list_page() -> bytes:
    return f"""
    <p>2件中 1-2件を表示中</p>
    <a href="/result/detail.php?rcl=00000035460&screenkbn=01">国内製造うどん - 回収</a>
    <span class="result_list_post_date">2026/06/24</span>
    <span class="result_list_start_date">2026/06/22</span>
    <a href="/result/detail.php?rcl=00000035456&screenkbn=01">中国産うなぎ - 回収</a>
    <span class="result_list_post_date">2026/06/22</span>
    <span class="result_list_start_date">2026/06/21</span>
    """.encode()


class JapanCandidateTests(unittest.TestCase):
    def test_new_recall_items_uses_url_state_as_baseline(self) -> None:
        current = [item(OTHER_URL), item(CHINA_URL)]
        self.assertEqual(
            [value.url for value in new_recall_items(current, [OTHER_URL])],
            [CHINA_URL],
        )

    def test_explicit_review_selects_current_url_already_in_baseline(self) -> None:
        selected, requested, scope = select_candidate_items(
            current_items=[item(OTHER_URL), item(CHINA_URL)],
            previous_urls=[OTHER_URL, CHINA_URL],
            review_urls=[CHINA_URL],
        )
        self.assertEqual([value.url for value in selected], [CHINA_URL])
        self.assertEqual(requested, [CHINA_URL])
        self.assertEqual(scope, "explicit_review")

    def test_explicit_review_rejects_url_outside_current_inventory(self) -> None:
        with self.assertRaisesRegex(ValueError, "not in the current food inventory"):
            select_candidate_items(
                current_items=[item(OTHER_URL)],
                previous_urls=[OTHER_URL],
                review_urls=[CHINA_URL],
            )

    def test_no_new_items_produces_empty_passing_report(self) -> None:
        report, records = build_candidate_report(
            items=[],
            schema=load_schema(SCHEMA),
            fetcher=lambda _: (_ for _ in ()).throw(AssertionError("unexpected fetch")),
            retrieved_at="2026-06-27T00:00:00+00:00",
            baseline_count=321,
            current_count=321,
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["candidate_url_count"], 0)
        self.assertEqual(records, [])

    def test_china_item_becomes_schema_valid_candidate(self) -> None:
        payloads = {
            CHINA_URL: caa_detail(china=True),
            MHLW_URL: mhlw_detail(),
        }
        report, records = build_candidate_report(
            items=[item(CHINA_URL, "中国産うなぎ - 回収")],
            schema=load_schema(SCHEMA),
            fetcher=payloads.__getitem__,
            retrieved_at="2026-06-27T00:00:00+00:00",
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["china_record_count"], 1)
        self.assertEqual(records[0]["source_record_id"], "RCL202601495")
        self.assertEqual(
            records[0]["authority"],
            "Ministry of Health, Labour and Welfare, Japan",
        )
        self.assertEqual(records[0]["source_url"], MHLW_URL)
        self.assertEqual(records[0]["event_date"], "2026-06-21")
        self.assertEqual(records[0]["origin_country"], "CN")
        self.assertEqual(records[0]["product_category"], "seafood")
        self.assertIn("labeling", records[0]["hazard_tags"])

    def test_tonburi_clostridium_maps_to_vegetable_microbiological(self) -> None:
        caa = caa_detail(china=True, mhlw=False).replace(
            "中国産うなぎ長焼".encode(), "とんぶり瓶詰（中国産）".encode()
        ).replace(
            "消費期限の誤表示".encode(),
            "芽胞菌（クロストリジウム属菌）を検出".encode(),
        )
        mhlw = mhlw_detail().replace(
            "中国産うなぎ長焼".encode(), "とんぶり瓶詰（中国産）".encode()
        ).replace(
            "食品表示法違反".encode(), "食品衛生法違反のおそれ".encode()
        ).replace(
            "期限表示の印字誤り".encode(),
            "芽胞菌（クロストリジウム属菌）を検出".encode(),
        )
        report, records = build_candidate_report(
            items=[item(CHINA_URL, "とんぶり瓶詰（中国産） - 回収")],
            schema=load_schema(SCHEMA),
            fetcher={CHINA_URL: caa, MHLW_URL: mhlw}.__getitem__,
            retrieved_at="2026-07-05T00:00:00+00:00",
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(records[0]["product_category"], "vegetables")
        self.assertEqual(records[0]["hazard_tags"], ["microbiological"])

    def test_non_china_item_is_reported_but_not_emitted(self) -> None:
        report, records = build_candidate_report(
            items=[item(OTHER_URL)],
            schema=load_schema(SCHEMA),
            fetcher=lambda _: caa_detail(china=False, mhlw=False),
            retrieved_at="2026-06-27T00:00:00+00:00",
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(records, [])
        self.assertEqual(report["page_results"][0]["status"], "parsed_non_china")

    def test_mhlw_backed_record_requires_mhlw_origin_evidence(self) -> None:
        payloads = {
            CHINA_URL: caa_detail(china=True),
            MHLW_URL: mhlw_detail(china=False),
        }
        report, records = build_candidate_report(
            items=[item(CHINA_URL)],
            schema=load_schema(SCHEMA),
            fetcher=payloads.__getitem__,
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(records, [])
        self.assertEqual(report["page_results"][0]["status"], "parsed_non_china")

    def test_candidate_minimum_mhlw_gate_fails_closed(self) -> None:
        payloads = {
            CHINA_URL: caa_detail(china=True),
            MHLW_URL: mhlw_detail(),
        }
        report, records = build_candidate_report(
            items=[item(CHINA_URL)],
            schema=load_schema(SCHEMA),
            fetcher=payloads.__getitem__,
            min_china_records=2,
            min_mhlw_records=2,
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["mhlw_backed_record_count"], 1)
        self.assertTrue(any("below minimum" in item for item in report["blocking_errors"]))

    def test_mhlw_identifier_mismatch_fails_closed(self) -> None:
        payloads = {
            CHINA_URL: caa_detail(china=True),
            MHLW_URL: mhlw_detail(rcl="RCL999999999"),
        }
        report, records = build_candidate_report(
            items=[item(CHINA_URL)],
            schema=load_schema(SCHEMA),
            fetcher=payloads.__getitem__,
            retrieved_at="2026-06-27T00:00:00+00:00",
        )
        self.assertEqual(report["status"], "failed")
        self.assertEqual(records, [])
        self.assertIn("MHLW recall ID mismatch", report["blocking_errors"][0])

    def test_candidate_pipeline_fetches_only_urls_newer_than_baseline(self) -> None:
        payloads = {
            CHINA_URL: caa_detail(china=True),
            MHLW_URL: mhlw_detail(),
        }
        fetched: list[str] = []

        def fetch(url: str) -> bytes:
            fetched.append(url)
            return payloads[url]

        with patch(
            "food_safety_watch.japan_candidates.load_url_state",
            return_value=[OTHER_URL],
        ):
            report, records = candidate_japan_caa(
                state_path=Path("unused-state.json"),
                schema=load_schema(SCHEMA),
                page_fetcher=lambda _: list_page(),
                fetcher=fetch,
            )

        self.assertEqual(report["baseline_count"], 1)
        self.assertEqual(report["current_count"], 2)
        self.assertEqual(report["candidate_url_count"], 1)
        self.assertEqual(len(records), 1)
        self.assertEqual(fetched, [CHINA_URL, MHLW_URL])

    def test_candidate_pipeline_supports_explicit_review_of_baseline_url(self) -> None:
        payloads = {
            CHINA_URL: caa_detail(china=True),
            MHLW_URL: mhlw_detail(),
        }
        with patch(
            "food_safety_watch.japan_candidates.load_url_state",
            return_value=[OTHER_URL, CHINA_URL],
        ):
            report, records = candidate_japan_caa(
                state_path=Path("unused-state.json"),
                schema=load_schema(SCHEMA),
                page_fetcher=lambda _: list_page(),
                fetcher=payloads.__getitem__,
                review_urls=[CHINA_URL],
            )
        self.assertEqual(report["scope"], "explicit_review")
        self.assertEqual(report["requested_urls"], [CHINA_URL])
        self.assertEqual(len(records), 1)


if __name__ == "__main__":
    unittest.main()
