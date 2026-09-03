from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_PROCESSED_FILES: dict[str, Path] = {
    "us_fda_import_refusals": Path("data/processed/fda_cn.jsonl"),
    "tw_tfda": Path("data/processed/taiwan_tfda_cn.jsonl"),
    "jp_caa_recalls": Path("data/processed/japan_mhlw_cn.jsonl"),
    "eu_rasff": Path("data/processed/rasff_cn.jsonl"),
}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            payload = json.loads(text)
            if not isinstance(payload, dict):
                raise ValueError(f"{path}:{line_number} is not a JSON object")
            records.append(payload)
    return records


def _shorten(text: str, *, limit: int = 420) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def _source_label(source: dict[str, Any]) -> str:
    region = str(source.get("authority_region") or source.get("id") or "")
    authority = str(source.get("authority") or source.get("id") or "")
    return f"{region} · {authority}" if region and authority else authority or region


def _public_record(record: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    reasons = [str(reason) for reason in record.get("reasons", []) if str(reason).strip()]
    hazard_tags = sorted(
        {str(tag) for tag in record.get("hazard_tags", []) if str(tag).strip()}
    )
    return {
        "id": str(record["id"]),
        "source_id": str(record["source_id"]),
        "source_label": _source_label(source),
        "source_record_id": str(record["source_record_id"]),
        "authority_region": str(record["authority_region"]),
        "action_type": str(record["action_type"]),
        "event_date": str(record["event_date"]),
        "origin_country": str(record.get("origin_country", "")),
        "record_status": str(record.get("record_status", "active")),
        "product_category": str(record.get("product_category", "")),
        "product_name": str(record.get("product_name", "")),
        "producer_name": str(record.get("producer_name", "")),
        "producer_location": str(record.get("producer_location", "")),
        "hazard_tags": hazard_tags,
        "reason_summary": _shorten(" / ".join(reasons)),
        "source_url": str(record["source_url"]),
    }


def _count(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(sorted(Counter(str(record.get(key, "")) for record in records).items()))


def _count_hazards(records: list[dict[str, Any]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for record in records:
        tags = record.get("hazard_tags", [])
        if tags:
            counter.update(str(tag) for tag in tags)
        else:
            counter["unknown"] += 1
    return dict(sorted(counter.items()))


def build_site_payload(
    *,
    sources_path: Path,
    processed_files: dict[str, Path] | None = None,
    generated_at: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build public records and summary for the static browser.

    Only implemented sources with a known processed JSONL file are included.
    Prototype/candidate sources can still have probes, but they do not enter the
    public data browser until their publication workflow is accepted.
    """

    sources = _read_json(sources_path)
    if not isinstance(sources, list):
        raise ValueError(f"{sources_path} must contain a JSON array")

    by_id = {
        str(source["id"]): source
        for source in sources
        if isinstance(source, dict) and "id" in source
    }
    paths = processed_files or DEFAULT_PROCESSED_FILES
    implemented_ids = [
        source_id
        for source_id, source in by_id.items()
        if source.get("status") == "implemented" and source_id in paths
    ]

    records: list[dict[str, Any]] = []
    missing_files: list[str] = []
    for source_id in sorted(implemented_ids):
        path = paths[source_id]
        if not path.exists():
            missing_files.append(str(path))
            continue
        for record in _read_jsonl(path):
            if str(record.get("source_id")) != source_id:
                raise ValueError(
                    f"{path} contains source_id={record.get('source_id')!r}; "
                    f"expected {source_id!r}"
                )
            records.append(_public_record(record, by_id[source_id]))

    records.sort(
        key=lambda record: (
            record["event_date"],
            record["source_id"],
            record["source_record_id"],
        ),
        reverse=True,
    )

    dates = [record["event_date"] for record in records if record.get("event_date")]
    summary = {
        "generated_at": generated_at
        or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "record_count": len(records),
        "implemented_sources": sorted(implemented_ids),
        "missing_files": missing_files,
        "date_min": min(dates) if dates else None,
        "date_max": max(dates) if dates else None,
        "by_source": _count(records, "source_id"),
        "by_region": _count(records, "authority_region"),
        "by_action_type": _count(records, "action_type"),
        "by_record_status": _count(records, "record_status"),
        "by_product_category": _count(records, "product_category"),
        "by_hazard_tag": _count_hazards(records),
    }
    return records, summary


def build_static_site(
    *,
    output_dir: Path,
    sources_path: Path = Path("data/sources.json"),
    processed_files: dict[str, Path] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    records, summary = build_site_payload(
        sources_path=sources_path,
        processed_files=processed_files,
        generated_at=generated_at,
    )

    data_dir = output_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "records.json").write_text(
        json.dumps(records, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    (data_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "index.html").write_text(_html(), encoding="utf-8")
    (output_dir / "README.md").write_text(_site_readme(summary), encoding="utf-8")
    return summary


def _site_readme(summary: dict[str, Any]) -> str:
    return (
        "# Food Safety Watch static browser\n\n"
        "Generated artifact for browsing explicitly published records from "
        "implemented sources.\n\n"
        f"- Generated at: `{summary['generated_at']}`\n"
        f"- Records: `{summary['record_count']}`\n"
        f"- Sources: `{', '.join(summary['implemented_sources'])}`\n\n"
        "Serve this directory with a static file server, for example:\n\n"
        "```powershell\n"
        "python -m http.server 8000 -d site\n"
        "```\n"
    )


def _html() -> str:
    return """<!doctype html>
<html lang="zh-Hans">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Check Chinese Food Safety</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f7f3eb;
      --panel: #fffaf0;
      --ink: #1e293b;
      --muted: #64748b;
      --line: #e7dcc9;
      --accent: #b45309;
      --accent-2: #047857;
      --chip: #fef3c7;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: radial-gradient(circle at top left, #fff7ed 0, var(--bg) 38rem);
      color: var(--ink);
    }
    header {
      padding: 3rem min(6vw, 5rem) 2rem;
      border-bottom: 1px solid var(--line);
    }
    .topbar {
      display: flex;
      justify-content: flex-end;
      margin-bottom: 1.5rem;
    }
    .lang-toggle {
      border: 1px solid var(--line);
      border-radius: 999px;
      background: #fffdf8;
      color: var(--ink);
      cursor: pointer;
      font: inherit;
      padding: 0.55rem 0.85rem;
    }
    h1 {
      margin: 0;
      font-size: clamp(2rem, 4vw, 4.5rem);
      letter-spacing: -0.055em;
      line-height: 0.95;
    }
    .subtitle {
      max-width: 58rem;
      margin-top: 1rem;
      color: var(--muted);
      font-size: 1.05rem;
      line-height: 1.7;
    }
    main { padding: 1.5rem min(6vw, 5rem) 4rem; }
    .stats {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
      gap: 1rem;
      margin-bottom: 1.5rem;
    }
    .stat, .filters, .record, .notice, .guide-card {
      background: rgba(255, 250, 240, 0.86);
      border: 1px solid var(--line);
      border-radius: 1.2rem;
      box-shadow: 0 18px 45px rgba(88, 62, 33, 0.08);
    }
    .stat { padding: 1rem; }
    .stat strong { display: block; font-size: 1.6rem; }
    .stat span { color: var(--muted); font-size: 0.9rem; }
    .notice {
      padding: 1rem 1.1rem;
      margin-bottom: 1rem;
      border-left: 0.35rem solid var(--accent-2);
      line-height: 1.7;
    }
    .notice strong { color: #065f46; }
    .guide-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(17rem, 1fr));
      gap: 1rem;
      margin-bottom: 1.25rem;
    }
    .guide-card {
      padding: 1rem;
    }
    .guide-card h2 {
      margin: 0 0 0.65rem;
      font-size: 1rem;
    }
    .guide-card dl {
      display: grid;
      gap: 0.65rem;
      margin: 0;
    }
    .guide-card dt {
      font-weight: 700;
      color: #334155;
    }
    .guide-card dd {
      margin: 0;
      color: var(--muted);
      font-size: 0.9rem;
      line-height: 1.55;
    }
    .filters {
      position: sticky;
      top: 0;
      z-index: 2;
      display: grid;
      grid-template-columns: 2fr repeat(4, minmax(9rem, 1fr));
      gap: 0.75rem;
      padding: 1rem;
      backdrop-filter: blur(16px);
      margin-bottom: 1.25rem;
    }
    input, select {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 0.85rem;
      padding: 0.75rem 0.85rem;
      background: #fffdf8;
      color: var(--ink);
      font: inherit;
    }
    .meta {
      color: var(--muted);
      font-size: 0.92rem;
      margin: 0 0 1rem;
    }
    .records {
      display: grid;
      gap: 1rem;
    }
    .record {
      padding: 1rem;
    }
    .record h2 {
      margin: 0 0 0.45rem;
      font-size: 1.05rem;
      line-height: 1.35;
    }
    .record a { color: var(--accent); text-decoration-thickness: 0.08em; }
    .chips {
      display: flex;
      flex-wrap: wrap;
      gap: 0.4rem;
      margin: 0.65rem 0;
    }
    .chip {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      background: var(--chip);
      border: 1px solid #fde68a;
      color: #713f12;
      padding: 0.2rem 0.55rem;
      font-size: 0.78rem;
      white-space: nowrap;
    }
    .reason {
      margin: 0.7rem 0 0;
      color: #334155;
      line-height: 1.65;
    }
    .empty {
      padding: 2rem;
      text-align: center;
      color: var(--muted);
    }
    footer {
      padding-top: 2rem;
      color: var(--muted);
      font-size: 0.9rem;
      line-height: 1.6;
    }
    @media (max-width: 900px) {
      .filters { grid-template-columns: 1fr; position: static; }
    }
  </style>
</head>
<body>
  <header>
    <div class="topbar">
      <button class="lang-toggle" id="lang-toggle" type="button">English</button>
    </div>
    <h1>Check Chinese Food Safety</h1>
    <p class="subtitle" id="subtitle">
      一个 evidence-first 的食品安全浏览器：只展示已经进入 implemented 来源、
      并通过发布门禁的官方记录。它不是健康建议，也不替代监管机构原文。
    </p>
  </header>
  <main>
    <section class="stats" id="stats"></section>
    <section class="notice">
      <strong id="notice-title">阅读边界：</strong>
      <span id="notice-text">
        这里展示的是监管机构已经公开的进口拒绝、边境不合格、召回或 RASFF 通报记录。
        它们代表具体批次、企业、申报或监管事件，不等于“某一种食品全部不安全”。
        判断时请优先打开每条记录的 official source 查看原文。
      </span>
    </section>
    <section class="guide-grid" aria-label="数据说明">
      <article class="guide-card">
        <h2 id="source-guide-title">来源怎么理解？</h2>
        <dl id="source-guide"></dl>
      </article>
      <article class="guide-card">
        <h2 id="hazard-guide-title">风险标签怎么理解？</h2>
        <dl id="hazard-guide"></dl>
      </article>
      <article class="guide-card">
        <h2 id="action-guide-title">措施类型怎么理解？</h2>
        <dl id="action-guide"></dl>
      </article>
    </section>
    <section class="filters" aria-label="筛选">
      <input id="q" type="search" placeholder="搜索产品、原因、企业、记录号…" autocomplete="off">
      <select id="source"></select>
      <select id="hazard"></select>
      <select id="action"></select>
      <select id="year"></select>
    </section>
    <p class="meta" id="meta">正在加载数据…</p>
    <section class="records" id="records"></section>
    <footer id="footer-note">
      数据来自各监管机构公开来源；本项目做了筛选、标准化与来源链接整理。
      请点击每条记录的 official source 查看监管机构原文。
    </footer>
  </main>
  <script>
    const state = { records: [], summary: {}, filters: {} };
    const els = {
      stats: document.querySelector("#stats"),
      langToggle: document.querySelector("#lang-toggle"),
      subtitle: document.querySelector("#subtitle"),
      noticeTitle: document.querySelector("#notice-title"),
      noticeText: document.querySelector("#notice-text"),
      sourceGuideTitle: document.querySelector("#source-guide-title"),
      hazardGuideTitle: document.querySelector("#hazard-guide-title"),
      actionGuideTitle: document.querySelector("#action-guide-title"),
      q: document.querySelector("#q"),
      source: document.querySelector("#source"),
      hazard: document.querySelector("#hazard"),
      action: document.querySelector("#action"),
      year: document.querySelector("#year"),
      sourceGuide: document.querySelector("#source-guide"),
      hazardGuide: document.querySelector("#hazard-guide"),
      actionGuide: document.querySelector("#action-guide"),
      meta: document.querySelector("#meta"),
      records: document.querySelector("#records"),
      footerNote: document.querySelector("#footer-note"),
    };
    const translations = {
      zh: {
        htmlLang: "zh-Hans",
        toggle: "English",
        subtitle: "一个 evidence-first 的食品安全浏览器：只展示已经进入 implemented 来源、并通过发布门禁的官方记录。它不是健康建议，也不替代监管机构原文。",
        noticeTitle: "阅读边界：",
        noticeText: "这里展示的是监管机构已经公开的进口拒绝、边境不合格、召回或 RASFF 通报记录。它们代表具体批次、企业、申报或监管事件，不等于“某一种食品全部不安全”。判断时请优先打开每条记录的 official source 查看原文。",
        sourceGuideTitle: "来源怎么理解？",
        hazardGuideTitle: "风险标签怎么理解？",
        actionGuideTitle: "措施类型怎么理解？",
        searchPlaceholder: "搜索产品、原因、企业、记录号…",
        allSources: "全部来源",
        allHazards: "全部风险",
        allActions: "全部措施类型",
        allYears: "全部年份",
        loading: "正在加载数据…",
        empty: "没有匹配记录。换个关键词试试。",
        more: count => `还有 ${count} 条匹配记录；请继续筛选。`,
        showing: (shown, total) => `显示 ${shown.toLocaleString()} / ${total.toLocaleString()} 条记录`,
        officialSource: "官方来源 / Official source",
        footer: "数据来自各监管机构公开来源；本项目做了筛选、标准化与来源链接整理。请点击每条记录的 official source 查看监管机构原文。",
        loadError: "数据加载失败。请确认你正在通过静态服务器打开 site/ 目录。",
        statLabels: {
          publishedRecords: "正式发布记录",
          implementedSources: "implemented 来源",
          eventDateRange: "事件日期范围",
          generatedAt: "生成时间",
        },
        label: {
          us_fda_import_refusals: "美国 FDA",
          tw_tfda: "台湾 TFDA",
          jp_caa_recalls: "日本 MHLW",
          eu_rasff: "欧盟 RASFF",
          import_refusal: "进口拒绝",
          inspection_failure: "查验不合格",
          rasff_notification: "RASFF 通报",
          recall: "召回",
          chemical: "化学风险",
          labeling: "标签/申报",
          microbiological: "微生物风险",
          adulteration: "掺假/真实性",
          other_or_unclassified: "其他/未分类",
        },
        sourceHelp: {
          us_fda_import_refusals: "美国 FDA 进口拒绝记录；表示具体进口申报被拒，不等于召回。",
          tw_tfda: "台湾 TFDA 边境查验不符合记录；包含产地、产品、原因和处置。",
          jp_caa_recalls: "日本 CAA/MHLW 召回体系中，经 MHLW detail 支撑的中国来源记录。",
          eu_rasff: "欧盟 RASFF 食品通报；本项目只发布人工复核过的中国来源 food 记录。",
        },
        hazardHelp: {
          chemical: "农残、兽残、污染物、添加物或其他化学性风险。",
          microbiological: "细菌、霉菌、病毒或卫生微生物指标相关风险。",
          labeling: "标签、过敏原、保质期、成分或申报信息不一致。",
          adulteration: "掺假、替代、非法成分或与产品真实性相关的问题。",
          other_or_unclassified: "官方原因尚不能稳定归入上述类别，需读原文判断。",
          unknown: "记录没有可发布的稳定风险标签。",
        },
        actionHelp: {
          import_refusal: "进口申报或货物被拒绝进入市场。",
          inspection_failure: "边境、抽检或官方检查中不符合要求。",
          rasff_notification: "欧盟成员或系统发布的 RASFF 食品安全通报。",
          recall: "监管或企业发起的召回、回收、退款或下架行动。",
        },
        fallbackHelp: "保留官方字段，点击记录 source 查看原文。",
      },
      en: {
        htmlLang: "en",
        toggle: "中文",
        subtitle: "An evidence-first food safety browser. It only shows official records from implemented sources that passed publication gates. It is not health advice and does not replace regulator source text.",
        noticeTitle: "Reading boundary: ",
        noticeText: "These are public import refusal, border inspection failure, recall, or RASFF notification records from regulators. They represent specific lots, firms, declarations, or regulatory events; they do not mean an entire food category is unsafe. Open the official source before drawing conclusions.",
        sourceGuideTitle: "How to read sources",
        hazardGuideTitle: "How to read risk tags",
        actionGuideTitle: "How to read action types",
        searchPlaceholder: "Search product, reason, firm, record ID…",
        allSources: "All sources",
        allHazards: "All risks",
        allActions: "All action types",
        allYears: "All years",
        loading: "Loading data…",
        empty: "No matching records. Try another keyword.",
        more: count => `${count} more matching records; narrow your filters to continue.`,
        showing: (shown, total) => `Showing ${shown.toLocaleString()} / ${total.toLocaleString()} records`,
        officialSource: "Official source",
        footer: "Data comes from public regulator sources. This project filters, normalizes, and links the records. Open each official source to read the regulator text.",
        loadError: "Failed to load data. Make sure you are serving the site/ directory with a static file server.",
        statLabels: {
          publishedRecords: "published records",
          implementedSources: "implemented sources",
          eventDateRange: "event date range",
          generatedAt: "generated at",
        },
        label: {
          us_fda_import_refusals: "US FDA",
          tw_tfda: "Taiwan TFDA",
          jp_caa_recalls: "Japan MHLW",
          eu_rasff: "EU RASFF",
          import_refusal: "Import refusal",
          inspection_failure: "Inspection failure",
          rasff_notification: "RASFF notification",
          recall: "Recall",
          chemical: "Chemical",
          labeling: "Labeling",
          microbiological: "Microbiological",
          adulteration: "Adulteration",
          other_or_unclassified: "Other / unclassified",
        },
        sourceHelp: {
          us_fda_import_refusals: "US FDA import refusal records; a refused import declaration is not the same thing as a recall.",
          tw_tfda: "Taiwan TFDA border inspection failures, with origin, product, reason, and disposition fields.",
          jp_caa_recalls: "Japan CAA/MHLW recall records; this site publishes only China-origin records backed by MHLW details.",
          eu_rasff: "EU RASFF food notifications; this project publishes only manually reviewed China-origin food records.",
        },
        hazardHelp: {
          chemical: "Pesticides, veterinary drugs, contaminants, additives, or other chemical risks.",
          microbiological: "Bacteria, mold, viruses, or hygiene microbiology indicators.",
          labeling: "Labeling, allergen, expiration date, ingredient, or declaration inconsistencies.",
          adulteration: "Adulteration, substitution, illegal ingredients, or product authenticity issues.",
          other_or_unclassified: "The official reason cannot yet be mapped reliably to the main categories; read the source text.",
          unknown: "No stable publishable risk tag is available for this record.",
        },
        actionHelp: {
          import_refusal: "An import shipment or declaration was refused entry.",
          inspection_failure: "A border, sampling, or official inspection did not meet requirements.",
          rasff_notification: "A food safety notification published through the EU RASFF system.",
          recall: "A regulator or firm initiated recall, refund, withdrawal, or removal action.",
        },
        fallbackHelp: "Official fields are preserved. Open the record source for context.",
      },
    };
    let language = localStorage.getItem("foodSafetyWatchLanguage") === "en" ? "en" : "zh";
    function text() {
      return translations[language];
    }
    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>"']/g, ch => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
      }[ch]));
    }
    function option(select, value, text) {
      const item = document.createElement("option");
      item.value = value;
      item.textContent = text;
      select.appendChild(item);
    }
    function unique(values) {
      return [...new Set(values.filter(Boolean))].sort();
    }
    function resetSelect(select, defaultText, values, labels) {
      const selected = select.value;
      select.textContent = "";
      option(select, "", defaultText);
      values.forEach(v => option(select, v, labels[v] || v));
      select.value = values.includes(selected) ? selected : "";
    }
    function setupFilters() {
      populateFilters();
      [els.q, els.source, els.hazard, els.action, els.year].forEach(el => el.addEventListener("input", render));
      els.langToggle.addEventListener("click", () => {
        language = language === "zh" ? "en" : "zh";
        localStorage.setItem("foodSafetyWatchLanguage", language);
        applyTranslations();
        renderGuides();
        renderStats();
        render();
      });
    }
    function populateFilters() {
      const copy = text();
      resetSelect(els.source, copy.allSources, unique(state.records.map(r => r.source_id)), copy.label);
      resetSelect(els.hazard, copy.allHazards, unique(state.records.flatMap(r => r.hazard_tags)), copy.label);
      resetSelect(els.action, copy.allActions, unique(state.records.map(r => r.action_type)), copy.label);
      resetSelect(els.year, copy.allYears, unique(state.records.map(r => r.event_date.slice(0, 4))).reverse(), {});
    }
    function applyTranslations() {
      const copy = text();
      document.documentElement.lang = copy.htmlLang;
      els.langToggle.textContent = copy.toggle;
      els.subtitle.textContent = copy.subtitle;
      els.noticeTitle.textContent = copy.noticeTitle;
      els.noticeText.textContent = copy.noticeText;
      els.sourceGuideTitle.textContent = copy.sourceGuideTitle;
      els.hazardGuideTitle.textContent = copy.hazardGuideTitle;
      els.actionGuideTitle.textContent = copy.actionGuideTitle;
      els.q.placeholder = copy.searchPlaceholder;
      els.footerNote.textContent = copy.footer;
      populateFilters();
    }
    function renderGuideList(target, values, help) {
      const copy = text();
      target.innerHTML = values.map(value => `
        <div>
          <dt>${escapeHtml(copy.label[value] || value)}</dt>
          <dd>${escapeHtml(help[value] || copy.fallbackHelp)}</dd>
        </div>
      `).join("");
    }
    function renderGuides() {
      const copy = text();
      renderGuideList(els.sourceGuide, unique(state.records.map(r => r.source_id)), copy.sourceHelp);
      renderGuideList(els.hazardGuide, unique(state.records.flatMap(r => r.hazard_tags)), copy.hazardHelp);
      renderGuideList(els.actionGuide, unique(state.records.map(r => r.action_type)), copy.actionHelp);
    }
    function renderStats() {
      const copy = text();
      const items = [
        [state.summary.record_count, copy.statLabels.publishedRecords],
        [Object.keys(state.summary.by_source || {}).length, copy.statLabels.implementedSources],
        [state.summary.date_min + " → " + state.summary.date_max, copy.statLabels.eventDateRange],
        [state.summary.generated_at, copy.statLabels.generatedAt],
      ];
      els.stats.innerHTML = items.map(([value, name]) =>
        `<article class="stat"><strong>${escapeHtml(value)}</strong><span>${escapeHtml(name)}</span></article>`
      ).join("");
    }
    function filtered() {
      const q = els.q.value.trim().toLowerCase();
      return state.records.filter(record => {
        if (els.source.value && record.source_id !== els.source.value) return false;
        if (els.hazard.value && !record.hazard_tags.includes(els.hazard.value)) return false;
        if (els.action.value && record.action_type !== els.action.value) return false;
        if (els.year.value && !record.event_date.startsWith(els.year.value)) return false;
        if (!q) return true;
        const haystack = [
          record.product_name, record.product_category, record.producer_name,
          record.producer_location, record.reason_summary, record.source_record_id,
          record.source_id, record.authority_region
        ].join(" ").toLowerCase();
        return haystack.includes(q);
      });
    }
    function render() {
      const copy = text();
      const rows = filtered();
      els.meta.textContent = copy.showing(rows.length, state.records.length);
      if (!rows.length) {
        els.records.innerHTML = `<div class="record empty">${escapeHtml(copy.empty)}</div>`;
        return;
      }
      els.records.innerHTML = rows.slice(0, 250).map(record => `
        <article class="record">
          <h2>${escapeHtml(record.product_name || "(unknown product)")}</h2>
          <div class="chips">
            <span class="chip">${escapeHtml(record.event_date)}</span>
            <span class="chip">${escapeHtml(copy.label[record.source_id] || record.source_id)}</span>
            <span class="chip">${escapeHtml(copy.label[record.action_type] || record.action_type)}</span>
            <span class="chip">${escapeHtml(record.product_category)}</span>
            ${record.hazard_tags.map(tag => `<span class="chip">${escapeHtml(copy.label[tag] || tag)}</span>`).join("")}
          </div>
          <div class="meta">
            ${escapeHtml(record.source_record_id)}
            ${record.producer_name ? " · " + escapeHtml(record.producer_name) : ""}
            ${record.producer_location ? " · " + escapeHtml(record.producer_location) : ""}
          </div>
          <p class="reason">${escapeHtml(record.reason_summary)}</p>
          <p class="meta"><a href="${escapeHtml(record.source_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(copy.officialSource)}</a></p>
        </article>
      `).join("");
      if (rows.length > 250) {
        els.records.insertAdjacentHTML("beforeend", `<div class="record empty">${escapeHtml(copy.more(rows.length - 250))}</div>`);
      }
    }
    async function main() {
      const [records, summary] = await Promise.all([
        fetch("data/records.json").then(r => r.json()),
        fetch("data/summary.json").then(r => r.json()),
      ]);
      state.records = records;
      state.summary = summary;
      setupFilters();
      applyTranslations();
      renderGuides();
      renderStats();
      render();
    }
    main().catch(error => {
      els.meta.textContent = text().loadError;
      els.records.innerHTML = `<pre class="record">${escapeHtml(error.stack || error)}</pre>`;
    });
  </script>
</body>
</html>
"""
