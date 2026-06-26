from __future__ import annotations

import json
import unittest

from food_safety_watch.canada_probe import (
    OPEN_DATA_JSON_URL,
    build_origin_probe_report,
    find_origin_evidence,
    has_china_mention,
    html_to_text,
    is_cfia_food_record,
    parse_open_data,
    select_probe_records,
)


DETAIL_URL = (
    "https://recalls-rappels.canada.ca/en/alert-recall/"
    "wu-xian-zhai-brand-soybean-snacks-recalled-due-undeclared-wheat-and-or-egg"
)


def open_data(records: list[dict[str, object]]) -> bytes:
    return json.dumps(records).encode("utf-8")


class CanadaProbeTests(unittest.TestCase):
    def test_parse_open_data_keeps_dict_records(self) -> None:
        records = parse_open_data(open_data([{"NID": "1"}, "bad", {"NID": "2"}]))
        self.assertEqual([record["NID"] for record in records], ["1", "2"])

    def test_cfia_food_record_requires_official_detail_url(self) -> None:
        self.assertTrue(is_cfia_food_record({"Organization": "CFIA", "URL": DETAIL_URL}))
        self.assertFalse(is_cfia_food_record({"Organization": "CFIA", "URL": "https://example.com"}))
        self.assertFalse(is_cfia_food_record({"Organization": "Medical devices", "URL": DETAIL_URL}))

    def test_select_probe_records_combines_latest_and_china_mentions(self) -> None:
        china_url = DETAIL_URL + "-china"
        records = [
            {"Organization": "Medical devices", "URL": DETAIL_URL, "NID": "skip"},
            {"Organization": "CFIA", "URL": DETAIL_URL, "NID": "1"},
            {
                "Organization": "CFIA",
                "URL": china_url,
                "NID": "2",
                "Title": "Chinese-style snacks recalled",
            },
        ]
        self.assertEqual(
            [
                record["NID"]
                for record in select_probe_records(
                    records,
                    latest_limit=1,
                    china_mention_limit=1,
                )
            ],
            ["1", "2"],
        )
        self.assertTrue(has_china_mention(records[2]))

    def test_origin_evidence_requires_explicit_origin_phrase(self) -> None:
        evidence = find_origin_evidence("Brand: China Best. Product: noodles.")
        self.assertEqual(evidence, [])
        evidence = find_origin_evidence("Country of origin: China. Product: noodles.")
        self.assertEqual(len(evidence), 1)
        self.assertTrue(evidence[0].mentions_china)

    def test_html_to_text_removes_markup(self) -> None:
        self.assertEqual(
            html_to_text(b"<html><script>bad()</script><p>Country&nbsp;of origin: China</p>"),
            "Country of origin: China",
        )

    def test_probe_report_samples_details_and_counts_evidence(self) -> None:
        records = [
            {
                "NID": "82236",
                "Title": "Soybean Snacks recalled",
                "URL": DETAIL_URL,
                "Organization": "CFIA",
                "Product": "Soybean Snacks",
                "Issue": "Egg - Wheat",
                "Category": "Candy",
                "Last updated": "2026-06-19",
            }
        ]
        payloads = {
            OPEN_DATA_JSON_URL: open_data(records),
            DETAIL_URL: b"<main><p>Country of origin: China</p></main>",
        }
        report = build_origin_probe_report(
            limit=10,
            china_mention_limit=10,
            fetcher=lambda url: payloads[url],
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["cfia_food_record_count"], 1)
        self.assertEqual(report["sampled_record_count"], 1)
        self.assertEqual(report["china_origin_evidence_page_count"], 1)
        self.assertEqual(report["page_results"][0]["status"], "china_origin_evidence")

    def test_probe_report_does_not_treat_china_mention_as_origin_evidence(self) -> None:
        records = [
            {
                "NID": "82236",
                "Title": "Chinese-style snacks recalled",
                "URL": DETAIL_URL,
                "Organization": "CFIA",
            }
        ]
        payloads = {
            OPEN_DATA_JSON_URL: open_data(records),
            DETAIL_URL: b"<main><p>Chinese-style snacks recalled due to allergen.</p></main>",
        }
        report = build_origin_probe_report(
            limit=10,
            china_mention_limit=10,
            fetcher=lambda url: payloads[url],
        )
        self.assertEqual(report["china_origin_evidence_page_count"], 0)
        self.assertEqual(report["page_results"][0]["status"], "no_origin_evidence")


if __name__ == "__main__":
    unittest.main()
