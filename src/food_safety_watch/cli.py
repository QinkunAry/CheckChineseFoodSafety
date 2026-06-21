from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import __version__
from .fda import download, parse_archive, write_jsonl
from .fsanz_smoke import build_smoke_report
from .quality import build_quality_report, load_schema, read_jsonl, write_json_file
from .update import QualityCheckFailed, update_fda


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="food-safety-watch")
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("sources", help="List registered official data sources")

    fetch = subparsers.add_parser("fetch-fda", help="Fetch and normalize FDA import refusals")
    fetch.add_argument("--country", default="CN", help="FDA two-letter country code")
    fetch.add_argument(
        "--archive", type=Path,
        help="Read an already downloaded FDA ZIP instead of downloading it",
    )
    fetch.add_argument(
        "--output", type=Path, default=Path("data/processed/fda_cn.jsonl"),
        help="Destination JSONL file",
    )

    validate = subparsers.add_parser("validate", help="Validate a JSONL data release")
    validate.add_argument("--input", type=Path, default=Path("data/processed/fda_cn.jsonl"))
    validate.add_argument("--schema", type=Path, default=Path("schemas/record.schema.json"))
    validate.add_argument("--report", type=Path, default=Path("reports/fda_quality.json"))
    validate.add_argument("--min-records", type=int, default=1_000)

    update = subparsers.add_parser(
        "update-fda", help="Fetch, validate and atomically publish FDA records"
    )
    update.add_argument("--country", default="CN")
    update.add_argument("--archive", type=Path)
    update.add_argument("--output", type=Path, default=Path("data/processed/fda_cn.jsonl"))
    update.add_argument("--schema", type=Path, default=Path("schemas/record.schema.json"))
    update.add_argument("--report", type=Path, default=Path("reports/fda_quality.json"))
    update.add_argument("--min-records", type=int, default=1_000)
    update.add_argument("--max-drop-percent", type=float, default=25.0)

    smoke = subparsers.add_parser(
        "smoke-fsanz", help="Read a small set of official FSANZ pages and report parser drift"
    )
    smoke.add_argument("--url", action="append", required=True, dest="urls")
    smoke.add_argument("--schema", type=Path, default=Path("schemas/record.schema.json"))
    smoke.add_argument("--report", type=Path, default=Path("reports/fsanz_smoke.json"))
    smoke.add_argument("--min-sitemap-recalls", type=int, default=100)
    smoke.add_argument("--min-china-records", type=int, default=0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "sources":
        sources = json.loads((_root() / "data" / "sources.json").read_text(encoding="utf-8"))
        for source in sources:
            print(f"{source['status']:<12} {source['id']:<28} {source['homepage']}")
        return 0

    if args.command == "fetch-fda":
        payload = args.archive.read_bytes() if args.archive else download()
        records = parse_archive(payload, country=args.country)
        count = write_jsonl(records, args.output)
        print(f"Wrote {count} records to {args.output}")
        return 0

    if args.command == "validate":
        records = read_jsonl(args.input)
        report = build_quality_report(
            records,
            load_schema(args.schema),
            source_id="us_fda_import_refusals",
            min_records=args.min_records,
        )
        write_json_file(report, args.report)
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        print(
            f"Validation {report['status']}: {report['record_count']} records; "
            f"report={args.report}"
        )
        return 0 if report["status"] == "passed" else 1

    if args.command == "update-fda":
        try:
            report = update_fda(
                output=args.output,
                report_path=args.report,
                schema_path=args.schema,
                country=args.country,
                archive=args.archive,
                min_records=args.min_records,
                max_drop_fraction=args.max_drop_percent / 100,
            )
        except QualityCheckFailed as error:
            print(error)
            return 1
        print(
            f"Published {report['record_count']} records to {args.output}; "
            f"quality report={args.report}"
        )
        return 0

    if args.command == "smoke-fsanz":
        report = build_smoke_report(
            urls=args.urls,
            schema=load_schema(args.schema),
            min_sitemap_recalls=args.min_sitemap_recalls,
            min_china_records=args.min_china_records,
        )
        write_json_file(report, args.report)
        print(
            f"FSANZ smoke {report['status']}: "
            f"{report.get('sitemap_recall_count', 0)} sitemap recalls; "
            f"{report.get('china_record_count', 0)} China records; report={args.report}"
        )
        return 0 if report["status"] == "passed" else 1

    return 2
