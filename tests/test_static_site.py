from __future__ import annotations

import json
import unittest
from pathlib import Path

from food_safety_watch.static_site import build_site_payload, build_static_site


def sample_record(
    *,
    source_id: str = "source_a",
    record_id: str = "record-1",
    event_date: str = "2026-01-02",
) -> dict[str, object]:
    return {
        "id": record_id,
        "source_id": source_id,
        "source_record_id": record_id,
        "authority": "Example Authority",
        "authority_region": "EX",
        "action_type": "recall",
        "event_date": event_date,
        "origin_country": "CN",
        "product_category": "tea",
        "product_name": "Green tea",
        "producer_name": "Example Producer",
        "producer_location": "Example City",
        "reasons": ["chemical residue", "label correction"],
        "hazard_tags": ["chemical", "labeling"],
        "source_url": "https://example.test/record-1",
        "retrieved_at": "2026-01-03T00:00:00+00:00",
    }


class StaticSiteTests(unittest.TestCase):
    def _tmp(self) -> Path:
        root = Path(".tmp-test/static-site")
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _write_jsonl(self, path: Path, records: list[dict[str, object]]) -> None:
        path.write_text(
            "\n".join(json.dumps(record) for record in records) + "\n",
            encoding="utf-8",
        )

    def test_payload_includes_only_implemented_sources(self) -> None:
        root = self._tmp()
        sources = root / "sources.json"
        source_a = root / "source_a.jsonl"
        source_b = root / "source_b.jsonl"
        sources.write_text(
            json.dumps(
                [
                    {
                        "id": "source_a",
                        "status": "implemented",
                        "authority": "Authority A",
                        "authority_region": "AA",
                    },
                    {
                        "id": "source_b",
                        "status": "candidate",
                        "authority": "Authority B",
                        "authority_region": "BB",
                    },
                ]
            ),
            encoding="utf-8",
        )
        self._write_jsonl(
            source_a,
            [
                sample_record(record_id="old", event_date="2025-12-31"),
                sample_record(record_id="new", event_date="2026-01-02"),
            ],
        )
        self._write_jsonl(source_b, [sample_record(source_id="source_b")])

        records, summary = build_site_payload(
            sources_path=sources,
            processed_files={"source_a": source_a, "source_b": source_b},
            generated_at="2026-01-04T00:00:00+00:00",
        )

        self.assertEqual([record["source_record_id"] for record in records], ["new", "old"])
        self.assertEqual(summary["record_count"], 2)
        self.assertEqual(summary["implemented_sources"], ["source_a"])
        self.assertEqual(summary["by_hazard_tag"], {"chemical": 2, "labeling": 2})
        self.assertEqual(summary["date_min"], "2025-12-31")
        self.assertEqual(summary["date_max"], "2026-01-02")

    def test_build_static_site_writes_browser_artifacts(self) -> None:
        root = self._tmp()
        sources = root / "sources.json"
        source_a = root / "source_a.jsonl"
        output = root / "site"
        sources.write_text(
            json.dumps(
                [
                    {
                        "id": "source_a",
                        "status": "implemented",
                        "authority": "Authority A",
                        "authority_region": "AA",
                    }
                ]
            ),
            encoding="utf-8",
        )
        self._write_jsonl(source_a, [sample_record()])

        summary = build_static_site(
            output_dir=output,
            sources_path=sources,
            processed_files={"source_a": source_a},
            generated_at="2026-01-04T00:00:00+00:00",
        )

        self.assertEqual(summary["record_count"], 1)
        self.assertTrue((output / "index.html").exists())
        self.assertTrue((output / "data" / "records.json").exists())
        self.assertTrue((output / "data" / "summary.json").exists())
        html = (output / "index.html").read_text(encoding="utf-8")
        self.assertIn("lang-toggle", html)
        self.assertIn("foodSafetyWatchLanguage", html)
        self.assertIn("How to read sources", html)
        self.assertIn("高频组合", html)
        self.assertIn("topRiskCombos", html)
        self.assertIn("Frequent combinations", html)
        self.assertIn("<details>", html)
        self.assertIn("recordDetails", html)
        self.assertIn("官方记录号", html)
        self.assertIn("Official record ID", html)
        self.assertIn("阅读边界", html)
        self.assertIn("风险标签怎么理解", html)
        self.assertIn("措施类型怎么理解", html)
        self.assertIn("sourceHelp", html)
        records = json.loads((output / "data" / "records.json").read_text(encoding="utf-8"))
        self.assertEqual(records[0]["source_label"], "AA · Authority A")

    def test_source_id_mismatch_fails_closed(self) -> None:
        root = self._tmp()
        sources = root / "sources.json"
        source_a = root / "source_a.jsonl"
        sources.write_text(
            json.dumps(
                [
                    {
                        "id": "source_a",
                        "status": "implemented",
                        "authority": "Authority A",
                        "authority_region": "AA",
                    }
                ]
            ),
            encoding="utf-8",
        )
        self._write_jsonl(source_a, [sample_record(source_id="wrong_source")])

        with self.assertRaisesRegex(ValueError, "expected 'source_a'"):
            build_site_payload(
                sources_path=sources,
                processed_files={"source_a": source_a},
            )


if __name__ == "__main__":
    unittest.main()
