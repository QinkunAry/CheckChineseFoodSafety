from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import __version__
from .canada_probe import build_origin_probe_report
from .cfs_candidates import candidate_cfs
from .cfs_inventory import inventory_cfs, write_url_state as write_cfs_url_state
from .cfs_smoke import build_smoke_report as build_cfs_smoke_report
from .fda import download, parse_archive, write_jsonl
from .fsanz_candidates import candidate_fsanz
from .fsanz_smoke import build_smoke_report
from .fsanz_inventory import inventory_fsanz, write_url_state
from .japan_candidates import candidate_japan_caa
from .japan_probe import build_japan_probe_report
from .japan_inventory import inventory_japan_caa, write_url_state as write_japan_url_state
from .japan_smoke import build_japan_smoke_report
from .korea_probe import build_korea_probe_report
from .quality import (
    build_quality_report,
    load_schema,
    read_jsonl,
    write_json_file,
    write_jsonl_file,
)
from .taiwan_probe import build_taiwan_probe_report
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

    inventory = subparsers.add_parser(
        "inventory-fsanz", help="Compare the official FSANZ sitemap with a URL baseline"
    )
    inventory.add_argument("--sitemap", type=Path)
    inventory.add_argument(
        "--state", type=Path, default=Path("data/state/fsanz_recall_urls.json")
    )
    inventory.add_argument(
        "--report", type=Path, default=Path("reports/fsanz_inventory.json")
    )
    inventory.add_argument(
        "--accept-current", action="store_true",
        help="Replace the URL baseline with the current official sitemap",
    )

    candidate = subparsers.add_parser(
        "candidate-fsanz",
        help="Parse only newly discovered FSANZ recall URLs into candidate records",
    )
    candidate.add_argument("--sitemap", type=Path)
    candidate.add_argument(
        "--state", type=Path, default=Path("data/state/fsanz_recall_urls.json")
    )
    candidate.add_argument("--schema", type=Path, default=Path("schemas/record.schema.json"))
    candidate.add_argument(
        "--output", type=Path, default=Path("data/candidates/fsanz_cn.jsonl")
    )
    candidate.add_argument(
        "--report", type=Path, default=Path("reports/fsanz_candidates.json")
    )

    cfs_smoke = subparsers.add_parser(
        "smoke-cfs", help="Read official Hong Kong CFS alert pages and report parser drift"
    )
    cfs_smoke.add_argument("--url", action="append", required=True, dest="urls")
    cfs_smoke.add_argument("--index-url", action="append", dest="index_urls")
    cfs_smoke.add_argument("--schema", type=Path, default=Path("schemas/record.schema.json"))
    cfs_smoke.add_argument("--report", type=Path, default=Path("reports/cfs_smoke.json"))
    cfs_smoke.add_argument("--min-index-alerts", type=int, default=1)
    cfs_smoke.add_argument("--min-china-records", type=int, default=1)

    cfs_inventory = subparsers.add_parser(
        "inventory-cfs", help="Compare official Hong Kong CFS alert indexes with a URL baseline"
    )
    cfs_inventory.add_argument("--index-url", action="append", dest="index_urls")
    cfs_inventory.add_argument(
        "--state", type=Path, default=Path("data/state/cfs_alert_urls.json")
    )
    cfs_inventory.add_argument(
        "--report", type=Path, default=Path("reports/cfs_inventory.json")
    )
    cfs_inventory.add_argument(
        "--accept-current", action="store_true",
        help="Replace the CFS URL baseline with the current official indexes",
    )

    cfs_candidate = subparsers.add_parser(
        "candidate-cfs",
        help="Parse only newly discovered Hong Kong CFS alert URLs into candidate records",
    )
    cfs_candidate.add_argument("--index-url", action="append", dest="index_urls")
    cfs_candidate.add_argument(
        "--state", type=Path, default=Path("data/state/cfs_alert_urls.json")
    )
    cfs_candidate.add_argument("--schema", type=Path, default=Path("schemas/record.schema.json"))
    cfs_candidate.add_argument(
        "--output", type=Path, default=Path("data/candidates/cfs_cn.jsonl")
    )
    cfs_candidate.add_argument(
        "--report", type=Path, default=Path("reports/cfs_candidates.json")
    )

    canada_probe = subparsers.add_parser(
        "probe-canada-origin",
        help="Sample official Canada CFIA food recalls and look for explicit origin evidence",
    )
    canada_probe.add_argument(
        "--input",
        type=Path,
        help="Read an already downloaded Canada open-data JSON file instead of downloading it",
    )
    canada_probe.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of latest CFIA food detail pages to inspect",
    )
    canada_probe.add_argument(
        "--china-mention-limit",
        type=int,
        default=20,
        help="Also inspect up to this many CFIA food records whose open-data text mentions China/Chinese",
    )
    canada_probe.add_argument(
        "--report",
        type=Path,
        default=Path("reports/canada_origin_probe.json"),
    )

    korea_probe = subparsers.add_parser(
        "probe-korea-recalls",
        help="Sample official Food Safety Korea recalls and explicit origin evidence",
    )
    korea_probe.add_argument(
        "--input",
        type=Path,
        help="Read an already downloaded Korea portal list JSON instead of requesting it",
    )
    korea_probe.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of latest recall detail pages to inspect",
    )
    korea_probe.add_argument(
        "--origin-mention-limit",
        type=int,
        default=20,
        help="Also inspect up to this many records with explicit country-origin wording",
    )
    korea_probe.add_argument("--min-china-records", type=int, default=0)
    korea_probe.add_argument(
        "--report",
        type=Path,
        default=Path("reports/korea_recall_probe.json"),
    )

    taiwan_probe = subparsers.add_parser(
        "probe-taiwan-tfda",
        help="Probe Taiwan TFDA border noncompliance open data",
    )
    taiwan_probe.add_argument("--input", type=Path)
    taiwan_probe.add_argument("--limit", type=int, default=10)
    taiwan_probe.add_argument("--min-records", type=int, default=2_000)
    taiwan_probe.add_argument("--min-china-records", type=int, default=300)
    taiwan_probe.add_argument(
        "--report", type=Path, default=Path("reports/taiwan_tfda_probe.json")
    )

    japan_probe = subparsers.add_parser(
        "probe-japan-caa",
        help="Sample official Japan CAA food recalls and MHLW references",
    )
    japan_probe.add_argument(
        "--input",
        type=Path,
        help="Read an already downloaded CAA food-list HTML file instead of downloading it",
    )
    japan_probe.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of latest CAA food detail pages to inspect",
    )
    japan_probe.add_argument(
        "--china-mention-limit",
        type=int,
        default=5,
        help="Also inspect up to this many current-list food records whose title mentions China",
    )
    japan_probe.add_argument(
        "--report",
        type=Path,
        default=Path("reports/japan_caa_probe.json"),
    )

    japan_smoke = subparsers.add_parser(
        "smoke-japan-caa",
        help="Read fixed official Japan CAA/MHLW recall pages and report parser drift",
    )
    japan_smoke.add_argument("--url", action="append", required=True, dest="urls")
    japan_smoke.add_argument(
        "--report",
        type=Path,
        default=Path("reports/japan_caa_smoke.json"),
    )
    japan_smoke.add_argument("--min-list-total", type=int, default=100)
    japan_smoke.add_argument("--min-china-records", type=int, default=1)
    japan_smoke.add_argument("--min-mhlw-references", type=int, default=1)

    japan_inventory = subparsers.add_parser(
        "inventory-japan-caa",
        help="Compare official Japan CAA food recall pages with a URL baseline",
    )
    japan_inventory.add_argument(
        "--state",
        type=Path,
        default=Path("data/state/japan_caa_recall_urls.json"),
    )
    japan_inventory.add_argument(
        "--report",
        type=Path,
        default=Path("reports/japan_caa_inventory.json"),
    )
    japan_inventory.add_argument(
        "--max-pages",
        type=int,
        help="Limit scanned CAA list pages for diagnostics; omit for full inventory",
    )
    japan_inventory.add_argument(
        "--accept-current",
        action="store_true",
        help="Replace the Japan CAA URL baseline with the current official list",
    )

    japan_candidate = subparsers.add_parser(
        "candidate-japan-caa",
        help="Parse newly discovered Japan CAA recalls into China-origin candidate records",
    )
    japan_candidate.add_argument(
        "--state",
        type=Path,
        default=Path("data/state/japan_caa_recall_urls.json"),
    )
    japan_candidate.add_argument(
        "--schema",
        type=Path,
        default=Path("schemas/record.schema.json"),
    )
    japan_candidate.add_argument(
        "--output",
        type=Path,
        default=Path("data/candidates/japan_caa_cn.jsonl"),
    )
    japan_candidate.add_argument(
        "--report",
        type=Path,
        default=Path("reports/japan_caa_candidates.json"),
    )
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

    if args.command == "inventory-fsanz":
        report, current_urls = inventory_fsanz(
            state_path=args.state,
            sitemap_path=args.sitemap,
        )
        write_json_file(report, args.report)
        if args.accept_current:
            write_url_state(current_urls, args.state)
        print(
            f"FSANZ inventory {report['status']}: {report['current_count']} current; "
            f"{report['new_url_count']} new; {report['removed_url_count']} removed; "
            f"report={args.report}"
        )
        return 0

    if args.command == "candidate-fsanz":
        report, records = candidate_fsanz(
            state_path=args.state,
            sitemap_path=args.sitemap,
            schema=load_schema(args.schema),
        )
        write_jsonl_file(records, args.output)
        write_json_file(report, args.report)
        print(
            f"FSANZ candidates {report['status']}: "
            f"{report['candidate_url_count']} new URLs; "
            f"{report['china_record_count']} China records; "
            f"output={args.output}; report={args.report}"
        )
        return 0 if report["status"] == "passed" else 1

    if args.command == "smoke-cfs":
        report = build_cfs_smoke_report(
            urls=args.urls,
            index_urls=args.index_urls,
            schema=load_schema(args.schema),
            min_index_alerts=args.min_index_alerts,
            min_china_records=args.min_china_records,
        )
        write_json_file(report, args.report)
        print(
            f"CFS smoke {report['status']}: "
            f"{report.get('index_alert_count', 0)} indexed alerts; "
            f"{report.get('china_record_count', 0)} China records; report={args.report}"
        )
        return 0 if report["status"] == "passed" else 1

    if args.command == "inventory-cfs":
        report, current_urls = inventory_cfs(
            state_path=args.state,
            index_urls=args.index_urls,
        )
        write_json_file(report, args.report)
        if args.accept_current:
            write_cfs_url_state(current_urls, args.state, index_urls=report["index_urls"])
        print(
            f"CFS inventory {report['status']}: {report['current_count']} current; "
            f"{report['new_url_count']} new; {report['removed_url_count']} removed; "
            f"report={args.report}"
        )
        return 0

    if args.command == "candidate-cfs":
        report, records = candidate_cfs(
            state_path=args.state,
            index_urls=args.index_urls,
            schema=load_schema(args.schema),
        )
        write_jsonl_file(records, args.output)
        write_json_file(report, args.report)
        print(
            f"CFS candidates {report['status']}: "
            f"{report['candidate_url_count']} new URLs; "
            f"{report['china_record_count']} China records; "
            f"output={args.output}; report={args.report}"
        )
        return 0 if report["status"] == "passed" else 1

    if args.command == "probe-canada-origin":
        payload = args.input.read_bytes() if args.input else None
        report = build_origin_probe_report(
            limit=args.limit,
            china_mention_limit=args.china_mention_limit,
            open_data_payload=payload,
        )
        write_json_file(report, args.report)
        print(
            f"Canada origin probe {report['status']}: "
            f"{report['cfia_food_record_count']} CFIA food records; "
            f"{report['sampled_record_count']} sampled; "
            f"{report['china_origin_evidence_page_count']} pages with China origin evidence; "
            f"report={args.report}"
        )
        return 0 if report["status"] == "passed" else 1

    if args.command == "probe-korea-recalls":
        payload = args.input.read_bytes() if args.input else None
        report = build_korea_probe_report(
            limit=args.limit,
            origin_mention_limit=args.origin_mention_limit,
            min_china_records=args.min_china_records,
            list_payload=payload,
        )
        write_json_file(report, args.report)
        print(
            f"Korea recall probe {report['status']}: "
            f"{report.get('portal_total_count')} portal records; "
            f"{report.get('sampled_record_count', 0)} sampled; "
            f"{report.get('china_origin_evidence_page_count', 0)} pages with China origin evidence; "
            f"report={args.report}"
        )
        return 0 if report["status"] == "passed" else 1

    if args.command == "probe-taiwan-tfda":
        payload = args.input.read_bytes() if args.input else None
        report = build_taiwan_probe_report(
            payload=payload,
            limit=args.limit,
            min_records=args.min_records,
            min_china_records=args.min_china_records,
        )
        write_json_file(report, args.report)
        print(
            f"Taiwan TFDA probe {report['status']}: "
            f"{report.get('record_count', 0)} records; "
            f"{report.get('china_record_count', 0)} China-origin; "
            f"{report.get('china_human_food_candidate_count', 0)} China food candidates; "
            f"report={args.report}"
        )
        return 0 if report["status"] == "passed" else 1

    if args.command == "probe-japan-caa":
        payload = args.input.read_bytes() if args.input else None
        report = build_japan_probe_report(
            limit=args.limit,
            china_mention_limit=args.china_mention_limit,
            list_payload=payload,
        )
        write_json_file(report, args.report)
        print(
            f"Japan CAA probe {report['status']}: "
            f"{report['list_total_count']} listed food recalls; "
            f"{report['sampled_record_count']} sampled; "
            f"{report['china_origin_evidence_page_count']} pages with China origin evidence; "
            f"{report['mhlw_reference_count']} MHLW references; "
            f"report={args.report}"
        )
        return 0 if report["status"] == "passed" else 1

    if args.command == "smoke-japan-caa":
        report = build_japan_smoke_report(
            urls=args.urls,
            min_list_total=args.min_list_total,
            min_china_records=args.min_china_records,
            min_mhlw_references=args.min_mhlw_references,
        )
        write_json_file(report, args.report)
        print(
            f"Japan CAA smoke {report['status']}: "
            f"{report.get('list_total_count')} listed food recalls; "
            f"{report.get('tested_page_count', 0)} tested pages; "
            f"{report.get('china_origin_evidence_page_count', 0)} China-origin pages; "
            f"{report.get('mhlw_reference_count', 0)} MHLW references; "
            f"report={args.report}"
        )
        return 0 if report["status"] == "passed" else 1

    if args.command == "inventory-japan-caa":
        report, current_urls = inventory_japan_caa(
            state_path=args.state,
            max_pages=args.max_pages,
        )
        write_json_file(report, args.report)
        if args.accept_current:
            write_japan_url_state(current_urls, args.state)
        print(
            f"Japan CAA inventory {report['status']}: "
            f"{report['current_count']} current; "
            f"{report['new_url_count']} new; "
            f"{report['removed_url_count']} removed; "
            f"report={args.report}"
        )
        return 0

    if args.command == "candidate-japan-caa":
        report, records = candidate_japan_caa(
            state_path=args.state,
            schema=load_schema(args.schema),
        )
        write_jsonl_file(records, args.output)
        write_json_file(report, args.report)
        print(
            f"Japan CAA candidates {report['status']}: "
            f"{report['candidate_url_count']} new URLs; "
            f"{report['china_record_count']} China records; "
            f"output={args.output}; report={args.report}"
        )
        return 0 if report["status"] == "passed" else 1

    return 2
