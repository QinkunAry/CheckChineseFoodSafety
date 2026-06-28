# Development Log / 每轮开发记录

本文件记录每轮开发的目标、实际改动、验证结果、发现的问题和下一步。它不是发布版本的营销式 Changelog，而是项目可追溯的工作日志。

## 记录规则

每次完成一轮实质工作后，在文件顶部追加一条记录，至少包含：

- 日期与轮次；
- 本轮目标；
- 已完成内容；
- 验证方式与结果；
- 新发现的问题或决策；
- 下一轮建议。

不得把“计划做”写成“已经完成”。外部数据数量应注明数据范围和抓取日期。

---

## 2026-06-28 · Round 32 · Korea read-only GitHub Action

### 本轮目标

补齐上一轮遗漏：将韩国只读 probe 接入 GitHub Actions，使 source spike 不只停留在本地命令。

### 本轮改动

- 新增 `.github/workflows/probe-korea-recalls.yml`；
- 支持手动 `workflow_dispatch` 和每周五定时运行；
- workflow 权限仅为 `contents: read`，不提交、不发布数据；
- 运行完整单元测试后读取韩国官方列表，并核验 1 条最新详情、已知中国来源和非中国产地对照；
- 新增 `--min-china-records`，workflow 设为 1，已知中国来源消失或解析失败时变红；
- 产地样本选择改为优先中国记录，再补其他国家产地记录，避免列表顺序变化漏掉已知样本；
- 无论成功失败都写入 Job Summary，并上传 `korea-recall-probe-report` artifact，保留 30 天；
- README 新增韩国 workflow badge，来源文档、registry 和 checklist 同步更新。

### 状态边界

新增 Action 不改变来源状态。韩国仍是 `candidate`：当前门槛 1 只用于监控已知样本；发现第二条明确中国来源后，才能将门槛提高到 2 并评估升级 `prototype`。

### 验证结果

- 全套 89 项单元测试通过；
- `probe-korea-recalls --help` 显示覆盖门槛参数；
- 最低中国样本门槛和中国优先抽样均有回归测试；
- `git diff --check` 通过（仅有 Windows LF/CRLF 提示）。

### 下一步建议

提交后手动运行 `Probe Korea Food Safety source`。若绿色，韩国进入等待第二条中国样本的监控状态，随后开始台湾 TFDA source spike。

---

## 2026-06-28 · Round 31 · Korea Food Safety Korea source probe

### 本轮目标

评估韩国 Food Safety Korea 是否能提供可自动读取、可明确证明中国产地、且具备可接受再利用条件的召回数据源。

### 官方来源发现

- 官方“회수·판매중지”页面通过同域 POST JSON endpoint 加载召回列表；
- 详情页使用数字 `rtrvldsuse_seq`，可直接读取产品名、登记日期、召回原因、经营者、地址、条码、召回等级和食品分类；
- 官方 OpenAPI 服务 `I0490` 提供 19 个召回字段，持续更新，但需要注册登录并申请认证 key；
- `I0490` metadata 标明需署名，可商用/非商用并允许制作衍生作品；
- `I0490` 输出字段没有制造国或原产国。

### 真实数据结果

2026-06-28 读取门户全部 359 条当前记录：

- 明确国家产地措辞的产品名 4 条；
- 明确中国来源 1 条；
- `mnf_natncd` 制造国字段非空 0 条；
- `incmfood_prdtcd` 进口产品代码非空 0 条；
- `prdlst_report_ledg_no` 可跨表报告号非空 0 条。

中国样本为 `3000227626`：`정성 가득 담은 고춧가루(중국산)`，登记日 2026-06-19，召回原因为金属性异物（铁粉）标准不合格。非中国对照 `3000227684` 明确写 `베트남산`（越南产）。

### 本轮改动

- 新增 `src/food_safety_watch/korea_probe.py`；
- 新增 `probe-korea-recalls` CLI；
- probe 读取官方门户 JSON，组合最新样本与明确产地措辞样本，并逐页核验官方详情；
- 仅接受 `중국산`、`중화인민공화국산`、`원산지: 중국`、`제조국: 중국` 等明确措辞；`중국식`、企业名和产品风格不算产地证据；
- 非官方 URL、非法编号、缺产品/日期/原因或结构漂移时失败关闭；
- 新增 7 项 Korea probe 测试；
- 新增 `docs/SOURCE_KOREA.md`，并更新 README、source registry、checklist 与 `.gitignore`。

### 决策

韩国保持 `candidate`。技术访问和再利用基础较好，但当前只有一条明确中国来源，未达到“两条中国 + 一条非中国”固定 smoke 门槛。生产自动化还需在申请 `I0490` key 与使用门户 endpoint 之间做正式选择；当前 probe 不发布数据。

### 验证结果

- 全套 88 项单元测试通过，包括“召回原因提到中国但产品并无中国产地证据”不得纳入的假阳性测试；
- 官方门户 JSON 返回 359/359 条记录；
- 使用真实官方 JSON 和三张真实详情页执行 probe，结果为 `passed`：3 个样本、1 条中国来源、0 个 blocking errors；
- 当前受管桌面环境拒绝 Python `urllib` 直接联网，因此官方响应通过 curl 下载后交给同一 probe 解析；默认联网命令仍需在普通本地环境或未来 GitHub Actions 中验证；
- `data/sources.json` 通过 JSON 解析。

### 下一轮建议

运行一次 live `probe-korea-recalls` 并保存诊断结果。若结果符合预期，韩国暂时等待第二条明确中国来源记录，项目转入台湾 TFDA source spike。

---

## 2026-06-27 · Round 30 · Japan expanded fixed smoke samples

### 本轮目标

完成 Japan prototype 的固定样本覆盖门槛：至少两条明确中国来源记录和一条非中国对照，避免 smoke 只验证单一页面结构。

### 本轮改动

- 新增中国来源固定样本 CAA `00000035471` / MHLW `RCL202601519`，商品为 `とんぶり瓶詰（中国産）`；
- 保留原中国来源样本 CAA `00000035456` / MHLW `RCL202601495`；
- 新增非中国对照 CAA `00000035460` / MHLW `RCL202601408`；
- workflow 门槛从 1 条中国记录、1 个 MHLW 引用提高为 2 条中国记录、3 个 MHLW 引用；
- 增加三页组合回归测试，验证 China/non-China 分流和引用计数；
- 更新 README、Japan source assessment、source registry 和 prototype checklist，移除“固定样本不足”阻断项。

### 真实 smoke 结果

2026-06-27 本地读取官方页面：CAA 食料品总数 321，固定详情 3 页，明确中国来源 2 页，MHLW 引用 3 个，smoke 状态 `passed`。第二条中国样本公开回收原因为检出芽胞菌（クロストリジウム属菌），対応開始日为 2026-06-12。

### 验证结果

- 全套 80 项单元测试通过；
- 三条固定官方详情和三个 MHLW 参照均可实时读取；
- `git diff --check` 通过（仅有 Windows LF/CRLF 提示）。

### 决策与剩余阻断

Japan 仍为 `prototype`。固定样本覆盖已完成；升级 `implemented` 前仍需首个非空 candidate batch 人工复核、最终 PDL 1.0 署名文案、生产质量门禁与发布 workflow。

### 下一轮建议

提交后重新运行 Japan workflow 验证三样本门槛。通过后进入韩国 Food Safety Korea source spike；Japan 等待未来新增 URL 形成非空候选批次。

---

## 2026-06-27 · Round 29 · Japan CAA incremental candidate pipeline

### 本轮目标

在 Japan smoke + inventory 之后增加只处理新增 URL 的 candidate 管线；继续保持只读 prototype，不写入 `data/processed/`。

### 本轮改动

- 新增 `src/food_safety_watch/japan_candidates.py` 和 `candidate-japan-caa` CLI；
- candidate 重新扫描 CAA 食料品分页，只处理不在 321 条 baseline 中的详情 URL；
- 解析 CAA 商品名、概要和対応開始日，并跟进页面公开的 MHLW `RCL...` 参照详情；
- MHLW hidden-field 解析新增 `DATE` 字段支持，可读取公开年月日和回收着手日期；
- 只有 CAA 或 MHLW 明确出现 `中国産`、`中華人民共和国産`、`原産国：中国` 或 `中国製` 才生成候选；
- MHLW 返回编号与 CAA 引用编号不一致、页面解析失败或 schema 错误时失败关闭；
- 日本语食品分类和 labeling/allergen/microbiological/chemical/adulteration 初始标签映射只用于候选检索；
- 新增 `tests/test_japan_candidates.py`，覆盖空增量、China/non-China 分流、统一 schema、日期、分类和 MHLW 编号不一致；
- GitHub workflow 在 smoke 和 inventory 后运行 candidate，并上传 ignored JSONL 与诊断报告；
- 更新 README、Japan source assessment、prototype checklist、source registry 和 `.gitignore`。

### 真实字段复核

2026-06-27 再次检查 CAA `00000035456` / MHLW `RCL202601495`：CAA 页面公开商品名、対応開始日 `2026年06月21日` 和 MHLW 引用；MHLW 页面公开 `_rcl_release_date_str=2026-06-22`、`_rcl_date_str=2026-06-21`、商品、回收原因与明确 `中国産` 文本。候选记录优先采用回收着手日期。

### 决策

- Japan 保持 `prototype`；candidate artifact 不是正式发布数据；
- baseline 不由 workflow 自动更新，必须在人工复核新候选后显式接受；
- 同一召回同时包含日本产与中国产商品时保留为候选，但必须人工确认产品粒度，不能自动当作纯中国商品事件发布；
- 正式发布仍受更广固定样本、首个非空候选批次人工复核、PDL 1.0 署名文案和生产质量门禁阻断。

### 验证结果

- 全套 79 项单元测试通过；
- `candidate-japan-caa --help` 正常；
- live candidate 扫描 321 条当前 URL，对比 321 条 baseline 后得到 0 new URLs、0 China records、0 schema errors，报告状态为 `passed`；
- `git diff --check` 通过（仅有 Windows LF/CRLF 提示）。

### 下一轮建议

提交后手动运行 Japan workflow。若 candidate 为空且 workflow 通过，下一步为 Japan 增加第二个中国来源和一个非中国固定 smoke 样本；若出现新 URL，则先人工复核 candidate artifact，再决定是否更新 baseline。

---

## 2026-06-27 · Round 28 · Japan CAA URL inventory baseline

### 本轮目标

把 Japan prototype 从固定样本 smoke 扩展到可发现新增 URL 的 inventory：扫描 CAA 食料品分页，建立 `data/state/` baseline，并让 GitHub Actions 每周报告新增/移除。

### 本轮改动

- 新增 `src/food_safety_watch/japan_inventory.py`；
- 新增 `inventory-japan-caa` CLI 命令；
- 新增 `tests/test_japan_inventory.py`，覆盖分页收集、`max_pages` 诊断限制、inventory diff、state round-trip 和非法 state 拒绝；
- 新增 `data/state/japan_caa_recall_urls.json` baseline；
- 更新 `.github/workflows/smoke-japan-caa.yml`，在 smoke 后比较 Japan CAA URL inventory，并上传 smoke/inventory reports；
- 将 workflow timeout 从 10 分钟调整为 20 分钟，避免 22 页官方分页扫描因站点慢而误失败；
- 更新 README、Japan source assessment、prototype checklist 和 `data/sources.json`。

### 官方分页发现

CAA 食料品列表使用表单分页。第一页为：

```text
https://www.recall.caa.go.jp/result/index.php?screenkbn=01&category=1
```

后续页面可向官方 `/result/index.php` POST：

- `screenkbn=01`
- `category=1`
- `viewCountdden=15`
- `portarorder=2`
- `actionorder=0`
- `pagingHidden={zero_based_page_index}`

实测第 2 页返回 `16-30件を表示中` 同类分页内容，并包含官方 detail URL。测试期间官方总数曾从 smoke 时的 322 变为 inventory 时的 321，因此以 inventory baseline 的 321 条唯一详情 URL 为准。

### 真实 inventory 结果

初始化 baseline：

```powershell
python -m food_safety_watch inventory-japan-caa --state data/state/japan_caa_recall_urls.json --report reports/japan_caa_inventory.json --accept-current
```

结果：

- reported CAA food recall total: 321；
- expected/scanned pages: 22；
- unique official CAA detail URLs: 321；
- new URLs vs empty baseline: 321；
- removed URLs: 0。

随后再次比较：

```powershell
python -m food_safety_watch inventory-japan-caa --state data/state/japan_caa_recall_urls.json --report reports/japan_caa_inventory.json
```

结果：`unchanged`，321 current，0 new，0 removed。

### 验证结果

- 本地全套 73 项单元测试通过；
- live Japan inventory baseline 生成成功；
- live Japan inventory 二次比较为 unchanged。

### 决策

Japan prototype 现在具备 smoke + inventory 两个基础门禁。它仍不能发布正式数据；下一步应做 `candidate-japan-caa`，只抓取 inventory 新增 URL，跟进 MHLW 参照详情，生成 ignored candidate JSONL 和诊断报告，供人工复核。

### 下一轮建议

实现 Japan candidate 管线，并补至少一个非中国固定样本和第二个中国来源样本，让 Japan 进入“可人工复核候选记录”的阶段。

---

## 2026-06-27 · Round 27 · Japan CAA / MHLW read-only smoke prototype

### 本轮目标

把日本 CAA / MHLW 从 probe 推进到只读 smoke prototype：能在本地和 GitHub Actions 中固定检查官方列表、CAA 详情页与 MHLW `RCL...` 参照详情，但仍不发布日本数据。

### 本轮改动

- 新增 `src/food_safety_watch/japan_smoke.py`；
- 新增 `smoke-japan-caa` CLI 命令；
- 新增 `tests/test_japan_smoke.py`，覆盖官方 URL 限制、MHLW URL 构造、China-origin evidence 门槛、列表数量门槛和失败关闭；
- 新增 `.github/workflows/smoke-japan-caa.yml`，每周只读运行，也支持手动触发；
- 将 `reports/japan_caa_smoke.json` 加入 `.gitignore`；
- 将日本来源在 `data/sources.json` 中从 `candidate` 调整为只读 `prototype`；
- 更新 README、Japan source assessment 和 prototype checklist，明确 Japan 仍不能写入 `data/processed/`。

### 真实 smoke 结果

命令：

```powershell
python -m food_safety_watch smoke-japan-caa --report reports/japan_caa_smoke.json --min-list-total 100 --min-china-records 1 --min-mhlw-references 1 --url "https://www.recall.caa.go.jp/result/detail.php?rcl=00000035456&screenkbn=01"
```

结果：

- CAA food list total: 322；
- first-page list items parsed: 15；
- fixed detail pages tested: 1；
- pages with explicit China-origin evidence: 1；
- MHLW references followed: 1；
- sample: CAA `00000035456` / MHLW `RCL202601495`。

### 验证结果

- 本地全套 68 项单元测试通过；
- live `smoke-japan-caa` 通过并生成 ignored diagnostic report。

### 决策

Japan 进入只读 `prototype`。这代表 parser/source-health gate 已存在；不代表可以发布正式数据。正式发布前仍需要 CAA 分页或 MHLW 搜索的增量发现、`data/state/` 基线、candidate 管线、至少两个中国来源和一个非中国固定样本、PDL 1.0 署名文案和人工复核。

### 下一轮建议

继续做 Japan inventory：研究 CAA form pagination 或 MHLW public search，建立只读 URL baseline，并让 workflow 能报告新增/移除的官方详情 URL。

---

## 2026-06-25 · Round 26 · Japan CAA / MHLW source probe

### 本轮目标

开始日本来源调研，确认 CAA recall portal 与 MHLW 食品衛生申請等システム是否适合作为中国来源食品 recall 数据源。

### 已发现

- CAA recall portal 可直接访问，HTML 服务端渲染；
- CAA category `1` 为 `食料品`；
- CAA 食料品列表在 2026-06-25 显示 320 条 food recall，第一页渲染 15 条；
- CAA 详情页包含标题、商品名、对象特定信息、対応開始日、備考、管理番号等字段；
- CAA 详情页可链接到 MHLW 食品衛生申請等システム公开回収详情；
- 样本 `00000035456` 对应 MHLW `RCL202601495`；
- MHLW 详情页可直接读取，并以 hidden text field 暴露稳定字段，例如 `_rcl_no_str`、`_rcl_product_str`、`_rcl_info_str`、`_rcl_rsn_type_str`、`_rcl_rsn_memo_str`；
- MHLW 与 CAA 页面均引用公共数据利用规约 PDL 1.0，需要出典标注；加工数据必须说明加工，不能表现为政府制作。

### 本轮改动

- 新增 `src/food_safety_watch/japan_probe.py`；
- 新增 `probe-japan-caa` CLI 命令；
- probe 读取 CAA 官方食料品列表，抽样 CAA 详情页，并跟进 MHLW `RCL...` 参照详情；
- 新增 Japan probe 单元测试，覆盖 CAA list、CAA detail、MHLW hidden field、明确 `中国産` origin evidence 与非证据文本分离；
- 新增 `docs/SOURCE_JAPAN.md`；
- 更新 `data/sources.json` 中日本来源的 authority、food list、MHLW public URL、access method 和 notes；
- 更新 README 与 prototype checklist；
- 将 `.tmp-japan/` 与 `reports/japan_caa_probe.json` 加入 `.gitignore`。

### 真实 probe 结果

命令：

```powershell
python -m food_safety_watch probe-japan-caa --limit 10 --china-mention-limit 5 --report reports/japan_caa_probe.json
```

结果：

- CAA food list total: 320；
- first-page list items parsed: 15；
- sampled detail pages: 10；
- sampled pages with MHLW reference links: 10；
- sampled pages with explicit China-origin evidence: 1；
- China-origin sample: CAA `00000035456` / MHLW `RCL202601495`，标题包含 `中国産うなぎ長焼`。

### 验证结果

- 全套 62 项单元测试通过；
- live Japan probe 通过并生成 ignored report。

### 决策

日本继续保持 `candidate`，但优先级高于加拿大。它已经证明有明确中国来源证据和 MHLW 稳定详情 ID；下一步应进入 `smoke-japan-caa` / inventory 设计，而不是转向其他国家。

### 下一轮建议

实现日本 prototype：固定两个中国来源样本和一个非中国样本，建立 `smoke-japan-caa`，然后研究 CAA 分页或 MHLW 搜索的安全增量发现方式。

---

## 2026-06-24 · Round 25 · Canada origin evidence probe

### 本轮目标

继续加拿大来源调研，用可复现命令验证 CFIA 食品 recall 详情页是否提供可用于中国来源过滤的明确原产地证据。

### 本轮改动

- 新增 `src/food_safety_watch/canada_probe.py`；
- 新增 `probe-canada-origin` CLI 命令；
- probe 从加拿大官方 English JSON feed 中筛选 CFIA 食品记录；
- probe 同时检查最新 CFIA 食品记录，以及 open-data 文本中提到 China/Chinese 的候选记录；
- 明确 China/Chinese mention 只用于寻找候选详情页，不等于 origin evidence；
- 只有 `Country of origin`、`Product of`、`Imported from`、`Manufactured in`、`Made in` 等明确短语才计为 origin evidence；
- 新增 Canada probe 单元测试，覆盖官方 URL 限制、CFIA 过滤、mention 与 origin evidence 分离、HTML 文本清理和 report 统计；
- 将 `reports/canada_origin_probe.json` 加入 `.gitignore`；
- 更新 Canada source assessment 与 README。

### 真实 probe 结果

命令：

```powershell
python -m food_safety_watch probe-canada-origin --limit 20 --china-mention-limit 20 --report reports/canada_origin_probe.json
```

结果：

- total open-data records: 33,692；
- CFIA food records: 5,243；
- CFIA food records with China/Chinese mentions: 12；
- sampled detail pages: 32；
- pages with any supported origin evidence phrase: 0；
- pages with China origin evidence: 0。

### 验证结果

- 全套 56 项单元测试通过；
- `python -m food_safety_watch sources` 可正常列出 Canada/Japan/Korea/Taiwan/EU 候选来源；
- live Canada probe 通过并生成 ignored report。

### 决策

加拿大继续保持 `candidate`，不进入 `prototype`。官方 open data 很适合 general food recall monitoring，但当前不适合本项目的“中国来源食品”事实数据，因为缺少稳定 origin evidence。

### 下一轮建议

转向日本 CAA source spike。若未来加拿大官方详情页或其他 CFIA 数据源提供稳定原产地字段，再回到 Canada prototype。

---

## 2026-06-24 · Round 24 · Canada source spike and Asia source queue

### 本轮目标

评估加拿大官方 recalls 数据源，并按用户建议将后续来源顺序调整为加拿大、日本、韩国、台湾，最后再回到欧盟。

### 已发现

- Government of Canada Recalls and Safety Alerts 门户说明 recall/alert 数据提供 CSV 和 JSON 格式，并每日更新；
- 2026-06-24 门户显示全类别 19,247 active、14,440 archived；
- 食品筛选页显示 1,203 条 Food 记录；
- Open Canada dataset `d38de914-c94c-429b-8ab1-8776c31643e3` 的 package metadata API 可访问；
- dataset 标题为 `Recalls and Safety Alerts`，许可证为 `Open Government Licence - Canada`；
- dataset notes 说明该网站是加拿大政府集中发布 food、consumer products、health products、medical devices、cannabis、vehicles recalls and safety alerts 的官方站点；
- 英文 JSON、英文 CSV 和 CFIA Food RSS feed 均可访问；
- 英文 JSON 记录字段包括 `NID`、`Title`、`URL`、`Organization`、`Product`、`Issue`、`Category`、`Recall class`、`Last updated`、`Archived`；
- CFIA 样本详情页字段丰富，但未发现稳定的 country-of-origin 字段。

### 本轮改动

- 新增 `docs/SOURCE_CANADA.md`；
- 在 `data/sources.json` 新增加拿大来源；
- 在 `data/sources.json` 新增日本 CAA、韩国 Food Safety Korea、台湾 TFDA 候选来源；
- 将欧盟 RASFF 在来源队列中延后，并在 notes 中说明；
- 更新 README，记录新的来源优先级和加拿大 blocker；
- 更新 checklist 当前来源状态表；
- 将 `.tmp-canada/` 加入 `.gitignore`。

### 决策

加拿大数据开放程度很好，但当前不能生成中国来源记录。除非找到明确的原产地/进口来源证据字段，否则只能用于 general food recall monitoring，不能进入本项目的中国食品发布数据。

### 下一轮建议

做 Canada deeper sampling：从官方 JSON 中筛选 CFIA Food 记录，抽样详情页查找是否存在 `country of origin`、`imported from`、`product of` 等稳定证据。如果找不到，加拿大保持 `candidate`，转向日本 CAA source spike。

---

## 2026-06-24 · Round 23 · EU RASFF source spike

### 本轮目标

评估欧盟 RASFF 是否可以作为下一条官方来源，并确定应该通过官方 API/数据门户还是页面抓取接入。

### 已发现

- European Commission RASFF 页面说明 RASFF Window 是公开的 summary notification 搜索入口，当前历史搜索限制为 2020 年以后；
- RASFF Window public configuration 暴露 `openPortalLink`，指向 data.europa 的 `restored_rasff` 数据集；
- data.europa metadata API 可返回 `restored_rasff` 的 JSON-LD；
- metadata 中存在 `Food and Feed Alert Notifications` JSON 分发，许可证标记为 `CC_BY_4_0`，修改时间为 2025-03-07；
- metadata 说明 API 数据对应 RASFF Window 公共信息，覆盖 2020 年以来通知，默认 JSON，也提供 CSV；
- metadata 还列出 pre-2021 XLSX 历史公共信息资源；
- metadata 中的 `APIs User Guide - Download` 在 2026-06-24 实测返回 404，尚不能确认实际 endpoint、鉴权方式和字段契约；
- DG SANTE developer portal 的 API 列表由自定义 widget 通过 runtime `managementApiUrl/apiVersion/token` 加载，静态 HTML 不暴露 RASFF API catalog；
- 常见 `/developer/apis` APIM catalog 猜测路径在 2026-06-24 返回 404 或 500，不能作为可实现端点。

### 本轮改动

- 新增 `docs/SOURCE_RASFF.md`，记录官方入口、许可证、覆盖范围、过滤原则和 blocker；
- 更新 `data/sources.json`，将 RASFF 的 access method 从泛化 research 更新为 data.europa/API 调研；
- 在发布前 checklist 的当前状态表中加入 EU RASFF；
- 更新 README，说明 RASFF 仍是 `candidate`，不能直接发布数据；
- 将 `.tmp-rasff/` 加入 `.gitignore`，避免调研临时文件进入提交。

### 决策

RASFF 不应抓取 Angular 页面作为主路径。下一步优先确认 DG SANTE DataLake API 或官方导出接口；在拿到 live sample payload 前，RASFF 不进入 `prototype`。

### 下一轮建议

继续 RASFF endpoint spike：检查 developer portal 是否需要注册/subscription key，寻找 OpenAPI 规格或可调用导出 URL。若能取得小样本，再实现 `smoke-rasff`；若不能，应转向另一个更开放的来源，例如新西兰 MPI、日本/韩国/加拿大官方 recall feed。

---

## 2026-06-24 · Round 22 · CFS reuse/attribution review

### 本轮目标

核对香港 CFS 官方版权/免责声明，判断该来源是否可以进入正式发布。

### 已发现

- CFS 页脚模板中的 `Copyright Notice` 与 `Disclaimer` 指向 `https://www.cfs.gov.hk/english/notices/notices.html`；
- 该 notice 将网站文本、图像和数据汇编等内容列为版权保护对象；
- 复制、改编、分发、传播或向公众提供这些版权作品，需要 Food and Environmental Hygiene Department 事先书面授权。

### 本轮修复

- 在 `docs/SOURCE_CFS.md` 增加 reuse review；
- 明确 CFS 在获得授权或等效复用依据前不能写入 `data/processed/`；
- 从 CFS smoke/candidate 诊断报告中移除官方标题文本，降低未授权公开传播的风险；
- CFS workflow 不再上传 `data/candidates/cfs_cn.jsonl` artifact，仅上传最小诊断报告；
- 更新 README 与 shared checklist 中 CFS 的 blocker。

### 决策

CFS 继续保持 `prototype`。当前可以做结构健康监控和最小诊断，但不能发布标准化 CFS 记录快照。

### 下一轮建议

若要推进 CFS 到 `implemented`，需要先联系或确认 FEHD/CFS 对标准化事实数据再利用的授权边界；否则应转向下一个来源 spike，例如欧盟 RASFF。

---

## 2026-06-24 · Round 21 · Prototype 到 implemented 发布前门禁

### 本轮目标

把 FSANZ/CFS 从 `prototype` 升级到 `implemented` 前必须完成的检查标准写清楚，避免“能抓取”被误认为“可发布”。

### 已完成

- 新增 `docs/PROTOTYPE_TO_IMPLEMENTED_CHECKLIST.md`；
- 将发布前门禁分为来源范围、版权/署名、发现与增量覆盖、字段证据、候选复核、数据质量、自动化失败处理、发布与回滚八类；
- 明确 `prototype` 来源只能生成 smoke、inventory 和 candidate artifact，不能写入 `data/processed/`；
- 在 FSANZ 与 CFS source assessment 中引用统一 checklist；
- 明确 FSANZ/CFS 当前共同 blocker：复用条款、候选批次人工复核、生产质量门禁、独立发布 workflow；
- 更新 README，说明新增来源升级前必须通过 checklist。

### 决策

以后来源状态变化必须和发布 gate 一起提交。不能只因为 parser、smoke 或 candidate workflow 成功，就把来源标记为 `implemented`。

### 下一轮建议

选择一个 prototype 来源先做 reuse/attribution review；建议从 CFS 开始，因为页面结构和样本范围更小。

---

## 2026-06-24 · Round 20 · 香港 CFS 新 URL 候选记录管线

### 本轮目标

在 CFS inventory workflow 手动运行成功后，建立 CFS 新增详情页的候选记录生成流程。

### 已完成

- 新增 `candidate-cfs` 命令；
- 新增 `cfs_candidates` 模块，按 `data/state/cfs_alert_urls.json` 只选择新增 URL；
- 对新增详情页执行官方 host 限制、字段解析、中国原产过滤和统一 Schema 校验；
- 输出候选 JSONL 到 `data/candidates/cfs_cn.jsonl`，诊断报告到 `reports/cfs_candidates.json`；
- 将候选管线接入只读 CFS workflow，以 artifact 形式保留结果，不提交、不发布、不更新基线；
- 补充单元测试覆盖无新增 URL、中国与非中国页面分流、解析失败诊断。

### 决策

CFS 候选记录仍不是正式发布数据。只有完成复核、版权/再利用条款确认、覆盖率评估后，才可以考虑将该来源升级为可发布数据源。

### 下一轮建议

手动运行 `Smoke test Hong Kong CFS source`。若通过，下一轮可以建立正式发布前的 review checklist，或转向欧盟 RASFF source spike。

---

## 2026-06-24 · Round 19 · 香港 CFS 增量 URL 基线

### 本轮目标

在 CFS smoke workflow 手动运行成功后，建立 CFS 官方年度列表的增量 URL 监控。

### 已完成

- 新增 `inventory-cfs` 命令；
- 新增 `cfs_inventory` 模块，支持读取多个官方年度 index 并合并去重详情 URL；
- 新增 `data/state/cfs_alert_urls.json`，保存 2026-06-24 当前 CFS 2026 当前列表与 2025 年列表的 36 条 alert URL 基线；
- 将 CFS inventory 接入 `smoke-cfs.yml`，作为只读诊断步骤和 artifact；
- 补充 CFS inventory 单元测试，覆盖新增/移除、跨年度合并、状态读写和非法状态；
- 更新 CFS 来源文档与 README，明确该基线不代表正式发布数据。

### 验证结果

- 首次 `--accept-current` 生成基线：36 current、36 new、0 removed；
- 第二次重复运行结果稳定：36 current、0 new、0 removed；
- 全套单元测试通过。

### 下一轮建议

实现 `candidate-cfs`：只抓取相对基线新增的 CFS alert 详情页，解析中国来源记录并生成候选 JSONL/report artifact，仍不发布正式数据。

---

## 2026-06-24 · Round 18 · 香港 CFS 来源 smoke prototype

### 本轮目标

接入第三个官方来源的最小可验证链路：香港 Centre for Food Safety 的 Food Alerts / Allergy Alerts 页面。

### 已完成

- 新增 `hk_cfs_alerts` 来源登记，状态为 `prototype`；
- 新增 `cfs` 解析模块，支持从官方年度列表发现详情 URL；
- 新增 CFS 详情页字段解析：标题、发布日期、食品产品、产品说明、`Place of origin` 和 `Reason For Issuing Alert`；
- 新增中国原产过滤，支持 `China` 及明确的中国大陆省级地区表述；
- 新增 `smoke-cfs` 命令；
- 新增只读 GitHub Actions workflow：`smoke-cfs.yml`；
- 新增 CFS 单元测试和 fixture，覆盖中国来源、非中国来源、缺失产地和 Schema smoke；
- 新增 `docs/SOURCE_CFS.md`，记录来源边界、过滤规则和 production gate。

### 决策

CFS 第一阶段只做 smoke，不发布正式数据，不做增量候选。等 live workflow 稳定后，再进入 `inventory-cfs` 与 `candidate-cfs`。

### 下一轮建议

手动运行 `Smoke test Hong Kong CFS source`。若通过，下一轮建立 CFS 年度列表 URL 基线，并按新增详情页生成候选记录 artifact。

---

## 2026-06-24 · Round 17 · FSANZ 新 URL 候选记录管线

### 本轮目标

在不发布 FSANZ 正式数据、不改写 URL 基线的前提下，让系统能处理官方 sitemap 中相对基线新增的召回详情页。

### 已完成

- 新增 `candidate-fsanz` 命令；
- 新增 `fsanz_candidates` 模块，按 `data/state/fsanz_recall_urls.json` 只选择新增 URL；
- 对新增详情页执行官方 host 限制、字段解析、中国原产过滤和统一 Schema 校验；
- 输出候选 JSONL 到 `data/candidates/fsanz_cn.jsonl`，诊断报告到 `reports/fsanz_candidates.json`；
- 将候选管线接入只读 FSANZ workflow，以 artifact 形式保留结果，不提交、不发布、不更新基线；
- 补充单元测试覆盖无新增 URL、中国与非中国页面分流、解析失败诊断。

### 决策

FSANZ 候选记录仍不是正式发布数据。只有完成复核、版权/再利用条款确认、覆盖率评估后，才可以考虑将该来源升级为可发布数据源。

### 下一轮建议

运行手动 FSANZ workflow，确认新增 candidate artifact 能在无新增 URL 时稳定生成空候选文件；随后开始设计正式数据发布前的人工 review checklist。

---

## 2026-06-24 · Round 16 · FSANZ scheduled smoke failure triage

### 诊断

- GitHub Actions 列表显示 `Smoke test FSANZ source #5` 定时运行失败，而 `#4` 手动运行通过；
- 本地沙箱网络复现为 sitemap 请求被拒绝，报告 `0 sitemap recalls`，该错误来自本地网络限制；
- 使用外部网络验证当前代码，`smoke-fsanz` 通过：345 条 sitemap recall URL，0 条中国记录；
- `inventory-fsanz` 通过：345 current，0 new，0 removed。

### 本轮修复

- 加固 GitHub Actions summary：如果 smoke 步骤失败导致 inventory 报告未生成，summary 不再无条件 `cat reports/fsanz_inventory.json`；
- 将 `reports/fsanz_smoke.json` 加入 `.gitignore`，避免本地 smoke 运行产物被误提交。

### 下一步

重新手动运行 `Smoke test FSANZ source`。如果当前 `main` 仍失败，需要打开失败 run 的 `FSANZ smoke diagnostic` 或 `Smoke test official FSANZ pages` 日志继续定位；如果通过，则进入 FSANZ 新 URL 候选记录生成阶段。

---

## 2026-06-22 · Round 15 · FSANZ 增量 URL 基线

### 本轮目标

在不重复请求全部历史详情、不发布未经授权数据的前提下，建立 FSANZ 新召回发现机制。

### 已完成

- 记录 live smoke 已成功验证真实 FSANZ 页面结构；
- 新增 `inventory-fsanz` 命令；
- 新增 sitemap 当前 URL 与已提交基线的集合比较；
- 报告新增 URL、移除 URL、当前数量和基线数量；
- 新增 `data/state/fsanz_recall_urls.json`，保存 2026-06-22 的 345 条官方召回 URL 基线；
- 首次重复比较结果为 345 current、0 new、0 removed；
- 将库存比较接入只读 smoke workflow；
- 库存报告进入 Job Summary 和诊断 artifact，但不自动提交或抓取新增详情；
- 新增排序、去重、变化检测、非法状态四类测试；
- 官方版权页已登记；在授权与署名正文核对完成前采用保守发布边界。

### 验证结果

- 全套 30 项单元测试通过；
- URL 基线重复运行结果稳定；
- `git diff --check` 通过；
- FSANZ 仍为 `prototype`，未发布任何新数据。

### 下一步

核对版权页适用许可和署名格式；随后实现“只抓新增 URL → 中国来源过滤 → Schema/数量门禁 → 候选数据”流程。历史回填单独限速执行。

---

## 2026-06-22 · Round 14 · FSANZ 真实 HTML 字段解析修复

### 诊断

第三次 smoke 已使用 `--min-china-records 0`，但六个详情页全部报告缺少 `Country of origin`。因此失败来自 HTML 字段提取，而不是中国记录数量门禁。

### 本轮修复

- 从只捕获特定标题、段落和 Drupal class，改为解析全部可见文本节点；
- 忽略 `script`、`style`、`noscript` 和 `svg`，防止脚本内容伪造证据字段；
- 支持 `dt/dd`、`span`、嵌套标签和“标签 + 值”同节点形式；
- 保持字段名精确匹配和官方域名限制；
- 页面仍解析失败时，在报告中加入与 country、origin、problem、hazard 相关的 `text_diagnostics`；
- 新增通用可见文本结构和脚本排除回归测试。

### 下一步

重新运行 smoke。若仍缺少原产国，使用 `text_diagnostics` 判断 FSANZ 是否改名或已从页面移除该字段；不能无证据推断原产地。

### 验证结果

- 全套 26 项单元测试通过；
- 通用 `dt/dd` 与嵌套 `span` 字段样本可生成中国召回记录；
- 脚本中的伪字段不会进入证据文本；
- 13 个 Python 文件通过 AST 解析；
- `git diff --check` 通过。

---

## 2026-06-22 · Round 13 · 拆分结构健康与中国覆盖率

### 问题

第二次 smoke 使用修复提交 `a98351d`，官方 sitemap 仍有 345 条召回，但六条固定样本没有中国原产记录。原工作流把“固定样本无中国记录”当成采集器故障，因此连续红灯不能准确表达系统状态。

### 本轮修复

- 新增独立的 `--min-china-records` 参数；
- 只读结构 smoke 使用 `0`，页面和字段正常时允许通过；
- 未来生产发布可将门槛设为 `1` 或更高，继续阻止空中国数据集发布；
- 即使中国记录为零，所有详情仍必须存在于 sitemap，并通过标题、日期、原因和原产国字段检查；
- 对实际发现的中国记录继续执行统一 Schema 验证；
- 将完整报告写入 GitHub Actions Job Summary，方便直接查看每页原产国；
- 增加“零中国结构通过”和“生产门禁拒绝零中国”回归测试。

### 决策

FSANZ 继续保持 `prototype`。结构 smoke 通过只表示来源可访问、解析器未漂移，不表示该来源已有足够中国食品覆盖率。

### 下一步

重新运行结构 smoke；若通过，结束页面解析稳定性验证，单独评估 FSANZ 中国记录覆盖率与接入价值。

### 验证结果

- 全套 24 项单元测试通过；
- 零中国结构检查和至少一条中国记录的生产门禁均有独立回归测试；
- 13 个 Python 文件通过 AST 解析；
- CLI 参数与 `git diff --check` 通过。

---

## 2026-06-22 · Round 12 · FSANZ smoke 首次真实反馈

### 运行结果

- 首次 GitHub Actions smoke run `27908563207` 成功读取官方 sitemap；
- sitemap 中发现 345 条召回详情；
- 三个名称看似与中国有关的固定样本没有产生中国原产记录；
- 任务按设计阻止了无证据记录进入数据层。

### 本轮修复

- 保持“必须由 `Country of origin` 明确证明”的规则，不根据名称放宽过滤；
- 新增独立详情检查器，非中国记录也完整验证标题、日期、原因和原产国；
- 诊断报告新增 `origin_country_text`，保留监管页原文；
- CLI 在 Actions 日志中打印完整 JSON 报告，不再依赖 artifact 下载才能诊断；
- 将三条无效候选替换为五条高概率进口候选，并保留一条澳洲零售产品作为非中国对照。

### 下一步

重新运行 smoke，以日志中的原产国原文确认至少一条中国记录；若候选仍不命中，继续替换候选，不能降低证据标准。

### 验证结果

- 全套 22 项单元测试通过；
- 工作流中的 6 条候选 URL 全部存在于已取得的官方 sitemap；
- 13 个 Python 文件通过独立 AST 解析；
- `git diff --check` 通过。

---

## 2026-06-21 · Round 11 · FSANZ 只读 smoke workflow

### 本轮目标

在不发布 FSANZ 数据的前提下，用 GitHub Actions 验证官方页面的真实结构和可访问性。

### 已完成

- 新增 `smoke-fsanz` 命令和纯函数式诊断报告生成器；
- 网络请求仅允许 FSANZ 官方 HTTPS 主机；
- 验证候选详情仍存在于官方 sitemap；
- sitemap 召回数量低于 100 时阻断，防止错误页被当成数据；
- 原产国字段缺失时明确失败，不再等同于“非中国来源”；
- 至少需要一条明确中国原产记录，并通过统一 Schema；
- 单页失败不妨碍继续检查其他页面，所有错误集中写入报告；
- 新增每周和手动触发的只读工作流，权限仅为 `contents: read`；
- 诊断报告无论成功失败都上传并保留 30 天；
- 工作流不提交、不发布任何 FSANZ 数据。

### 验证结果

- 全套 21 项单元测试通过；
- 网络失败可生成包含异常类型的诊断报告；
- 中国与非中国页面组合可通过 sitemap、Schema 和最小记录门禁；
- 13 个 Python 文件完成独立 AST 语法解析；
- `smoke-fsanz --help` 与 `git diff --check` 通过。

### 下一步

提交后手动运行 `Smoke test FSANZ source`。根据真实 artifact 修正字段解析；只有 smoke 通过且再利用条款确认后，才设计增量缓存和生产发布。

---

## 2026-06-21 · Round 10 · FSANZ 第二来源原型

### 本轮目标

选择第二个监管来源，并验证召回数据能否在不依赖 AI 的情况下进入统一事实层。

### 已完成

- 对澳新 FSANZ 与新西兰 MPI 做 source spike；
- 确认 FSANZ 旧召回路径已失效，登记当前召回页和官方 sitemap；
- 新增 FSANZ sitemap 召回详情 URL 发现器；
- 新增语义字段解析原型，提取标题、发布日期、问题、食品安全危害和原产国；
- 只有官方 `Country of origin` 明确写明中国、PRC 或中华人民共和国英文名时才纳入；
- 不根据产品名、菜系、进口商或 URL 推断中国原产；
- 新增官方域名限制、稳定 ID、统一分类和风险标签输出；
- 新增中国来源、非中国来源、sitemap 去重和非官方 URL 四类回归测试；
- 新增 `docs/SOURCE_FSANZ.md`，记录证据规则、访问问题和生产门禁；
- 来源登记状态设为 `prototype`，尚未启用自动发布。

### 已知问题

- FSANZ sitemap 可访问，但本地环境对详情页和 JSON:API 的重复请求超时；
- 当前选择器使用固定代表性样本验证，仍需在 GitHub Actions 中用新鲜官方页面验收；
- 发布数据前还需确认 FSANZ 数据再利用和署名条件；
- MPI 页面触发 Incapsula，暂缓接入，不尝试绕过访问控制。

### 验证结果

- 全套 18 项单元测试通过；
- FSANZ 中国来源样本可生成统一 `recall` 记录和稳定 ID；
- 非中国来源样本被排除；
- FDA 现有 2,590 条记录继续通过 Schema 和质量检查；
- `git diff --check` 通过。

### 下一步

为 FSANZ 增加只读 smoke test，在 GitHub Actions 中抓取少量官方详情并保存诊断 artifact；真实字段通过后，再实现全量增量缓存、质量门禁和定时发布。

---

## 2026-06-21 · Round 9 · 自动更新失败通知

### 本轮目标

让定时更新失败可见，并在恢复后自动关闭故障记录。

### 已完成

- 为 FDA 更新工作流增加最小化的 `issues: write` 权限；
- 任一步骤失败时创建 `[automation] FDA data update failed` Issue；
- 已存在同标题开放 Issue 时只追加评论，避免重复告警；
- 告警内容包含工作流链接、分支、提交和触发方式；
- 明确说明旧版验证数据仍然可用；
- 后续运行成功时自动评论恢复链接并关闭故障 Issue；
- 使用 GitHub 官方 `actions/github-script@v8`，不引入第三方告警 Action。

### 验证状态

- YAML 与脚本已完成静态检查；
- GitHub 权限和 API 行为需在提交后由实际工作流验证；
- 不通过故意破坏生产数据任务来制造测试故障。

### 下一步

提交并同步机器人数据提交，运行一次正常更新确认恢复步骤不影响成功路径。之后开始第二监管来源的 source spike。

---

## 2026-06-21 · Round 8 · 首次自动更新成功

### 本轮目标

独立验收 GitHub Actions 首次完整 FDA 自动更新。

### 结果

- 工作流 run `27883035132` 使用提交 `e72a6f3`；
- 触发方式为 `workflow_dispatch`；
- 最终状态为 `completed / success`；
- 质量报告状态为 `passed`；
- 发布记录 2,590 条，唯一 ID 2,590 个；
- 重复 ID 为 0，Schema 错误为 0；
- 相对基线数量变化为 0%；
- 质量报告 artifact `fda-quality-report` 已生成并保留 30 天；
- `github-actions[bot]` 已创建提交 `9948c7c`，证明仓库写权限和自动回写正常。

### 结论

M2 的基础闭环已经跑通：定时触发、官方数据下载、解析、质量门禁、artifact 留存和验证后自动提交均可工作。

### 下一步

本地仓库先同步机器人提交，然后增加失败通知；之后开始评估并接入第二个监管来源。

---

## 2026-06-21 · Round 7 · 空镜像变量修复

### 本轮目标

修复 GitHub Actions 在未配置镜像变量时把空字符串作为下载 URL 的问题。

### 故障

- 新工作流已使用修复提交，但 curl 收到的最终 URL 为 `''`；
- GitHub 表达式 `${{ vars.FOOD_SAFETY_FDA_DOWNLOAD_URL }}` 在变量不存在时向进程注入空字符串；
- 下载器只判断 `None`，没有将空字符串归一化，因此跳过官方页面发现逻辑。

### 已完成

- 新增 `configured_download_url()`；
- 对环境变量执行 `strip()`；
- 空字符串和纯空白字符串统一视为未配置；
- 只有显式 URL 或非空镜像变量才覆盖官方动态发现；
- 增加两个 GitHub 空变量回归测试。

### 下一步

提交修复并从工作流主页对 `main` 创建一次全新的手动运行。

---

## 2026-06-21 · Round 6 · GitHub Runner 下载故障修复

### 本轮目标

诊断首次 `Update FDA data` 手动运行失败，并提高 FDA 下载器对云端 Runner 的兼容性与可诊断性。

### 故障

- GitHub Actions run `27877436765` 在 FDA ZIP 下载阶段失败；
- GitHub 托管 Runner 访问硬编码 ZIP 时经重定向得到 HTTP 404；
- 同一官方 URL 在本地于 2026-06-21 返回 HTTP 200 和约 5.03 MB ZIP；
- 因此故障发生在 FDA/CDN 与 GitHub Runner 网络之间，而非文件名变化、解析器或质量门禁。

### 已完成

- 下载前访问 FDA 官方页面并动态发现当前 `*-present.zip` 文件名；
- 同一 curl 会话保存 Cookie，并为 ZIP 请求附带 Referer；
- 使用浏览器兼容 User-Agent、HTTP/1.1、连接超时和三次重试；
- 下载后验证内容确实为 ZIP，拒绝 HTML 错误页；
- 增加 `FdaDownloadError`，提供比 `CalledProcessError` 更明确的故障信息；
- 支持仓库变量 `FOOD_SAFETY_FDA_DOWNLOAD_URL`，为经批准的同内容镜像预留后端切换能力；
- 增加动态发现和不安全文件名回归测试。

### 验证

- 12 项单元测试通过；
- 本地官方页面仍列出 `Import_Refusal_2024-present.zip`；
- 本地官方 ZIP 响应为 HTTP 200；
- 使用现有官方 ZIP 的完整更新仍发布 2,590 条记录并通过质量门禁；
- GitHub Runner 修复效果等待下一次手动运行确认。

### 下一步

提交本轮修复并重新运行 `Update FDA data`。如果 FDA 仍按 Runner IP 拒绝请求，则停止继续伪装请求，改用自托管 Runner 或可信镜像。

---

## 2026-06-21 · Round 5 · GitHub 仓库与首次 CI 验证

### 本轮目标

确认本地 Git 初始化、GitHub remote、初始提交和 Actions 运行状态。

### 已完成

- 确认本地分支 `main` 与 `origin/main` 同步；
- 确认远程仓库为 `https://github.com/QinkunAry/CheckChineseFoodSafety.git`；
- 确认初始提交 `346caf2` 已包含 CI、FDA 更新工作流、发布数据与质量报告；
- 通过 GitHub API 确认仓库公开且默认分支为 `main`；
- 确认首次 `CI` 工作流运行成功；
- 在 README 增加 CI、FDA 更新状态徽章和仓库链接；
- 在 `pyproject.toml` 增加 Repository 与 Issues 元数据。

### 验证

- 本地工作树在文档更新前为干净状态；
- `HEAD`、`main` 与 `origin/main` 均指向 `346caf2`；
- GitHub CI run `27877322570` 状态为 `completed / success`。

### 尚未完成

- `Update FDA data` 尚未执行首次手动运行；
- 本机没有 GitHub CLI，无法从当前环境发起带认证的 `workflow_dispatch`；
- 本轮新增的 README、项目元数据和开发日志需要由用户提交并推送。

### 下一步

在 GitHub Actions 页面手动运行一次 `Update FDA data`，确认下载、质量 artifact 和自动提交权限均正常。

---

## 2026-06-20 · Round 4 · Schema 验证与自动更新

### 本轮目标

进入 M2，将 FDA 管道从手动生成升级为带质量门禁的自动更新流程。

### 已完成

- 增加 `jsonschema` 4.26 系列依赖；
- 使用 Draft 2020-12 验证统一记录；
- 将事件日期和抓取时间分别约束为 `date` 与 `date-time`；
- 新增 `validate` 命令，可验证已有 JSONL 并生成质量报告；
- 新增 `update-fda` 命令，先验证候选，再发布结果；
- 增加最小记录数、重复 ID、Schema 错误和相对基线下降 25% 的阻断条件；
- 质量报告包含记录数、时间范围、食品分类和风险标签分布；
- 自动更新保留既有记录的首次抓取时间，避免无意义的全文件变更；
- 增加小型 FDA CSV 回归样本；
- 增加 CI 与每周 FDA 更新两个 GitHub Actions 工作流；
- 将验证后的 `fda_cn.jsonl` 和质量报告纳入发布文件。

### 验证

- 10 项单元测试通过；
- 当前 2,590 条 FDA 中国人类食品记录通过 JSON Schema 验证；
- 重复稳定 ID：0；
- 当前事件日期范围：2024-01-02 至 2026-05-29；
- 使用同一官方 ZIP 重复更新前后，JSONL SHA-256 完全一致；
- 模拟低于最小记录数时，质量检查失败且发布函数不会被调用。

### 发现的问题与处理

- 受管 Windows 环境限制 Python 临时目录和原子重命名，因此实现采用“内存中完整验证后再写发布文件”；质量失败仍不会覆盖旧数据；
- 自动下载在 GitHub Linux runner 上尚需仓库推送后的首次手动工作流验证；
- 已定位本地 Git：`D:\Program Files\Git\cmd\git.exe`，版本 2.54.0；
- 当前项目尚未初始化为 Git 仓库；Codex 受管进程对 `.git` 目录存在显式写入拒绝，因此无法代替用户执行首次 `git init`；
- 首次初始化完成后，仍需检查 Git diff、创建初始提交并配置 GitHub remote。

### 决策

- 自动任务不使用 AI Agent；
- 官方数据候选只有通过质量门禁后才能进入发布文件；
- 既有记录保留首次 `retrieved_at`，新增记录才使用本轮抓取时间；
- 自动数据刷新由质量报告记录，不自动改写开发日志。

### 下一轮建议

把项目推送到 GitHub，手动运行一次 `Update FDA data` 工作流；确认权限与提交行为后，再增加失败通知和第二个监管来源。

---

## 2026-06-20 · Round 3 · 补齐产品治理文档

### 本轮目标

将最终产品目标与逐轮开发记录从 README 和架构说明中独立出来，形成长期维护的项目文件。

### 已完成

- 新建 `PRODUCT_GOALS.md`；
- 定义产品愿景、原则、最终形态、用户、范围和非目标；
- 将路线拆分为 M1 至 M6；
- 明确核心系统不依赖 AI Agent 或 OpenClaw；
- 新建本开发日志并制定后续追加格式；
- 在 README 中增加产品目标和开发日志入口。

### 验证

- 检查产品目标是否同时覆盖数据、网站、API、AI、skills 和 iOS；
- 检查里程碑是否有完成标准；
- 检查 AI 与监管事实的边界是否明确。

### 决策

- `PRODUCT_GOALS.md` 负责回答“最终做成什么”；
- `DEVELOPMENT_LOG.md` 负责回答“每轮做了什么”；
- `README.md` 只保留项目入口和快速开始；
- `FUTURE_AI_PLAN.md` 继续负责 AI 专题设计。

### 下一轮建议

推进 M2 的第一部分：为 FDA 数据增加 schema 自动验证、数据质量报告和固定回归样本。

---

## 2026-06-20 · Round 2 · 最终产品架构讨论

### 本轮目标

明确最终版本是否依赖 AI Agent、OpenClaw 或 skills。

### 已完成

- 确定最终产品由开放数据集、消费者网站、API、AI 助手和第三方集成构成；
- 确定数据管道和事实数据库是核心；
- 确定 AI 是解释与交互层；
- 确定 OpenClaw、Codex 等 skills 是可替换的接入层；
- 确定 iOS App 复用同一 API，不维护独立事实源。

### 验证

- 架构能够在关闭 AI 和第三方 Agent 后继续采集、更新、查询数据；
- 每一层都可以被替换而不破坏事实数据。

### 决策

项目不绑定任何 Agent 框架。未来 skills 只调用公开 API，不能直接改写监管事实。

### 下一轮建议

将讨论结果正式写入产品目标文档，并建立逐轮开发日志。

---

## 2026-06-20 · Round 1 · MVP 骨架与 FDA 真实数据验证

### 本轮目标

确定项目第一个可执行目标，并打通一个真实官方数据源。

### 已完成

- 确定第一目标是可验证的数据管道，而非 Agent 或 skills；
- 建立 Python 标准库项目骨架；
- 创建来源登记、统一 schema、架构说明和 AI 后续计划；
- 核验 FDA Import Refusal Report 官方 ZIP/CSV；
- 解析拒绝记录与 `ACT_SECTION_CHARGES` 原因表；
- 根据 FDA Product Code Builder 建立人类食品行业白名单；
- 排除太阳镜、医疗器械、动物饲料等非目标记录；
- 添加稳定 ID、食品类别、风险标签和 ISO 日期；
- 修复 `misleading` 被子串 `lead` 误判为化学风险的问题。

### 数据结果

- 官方数据包范围：2024 至 2026 年 5 月；
- 原产地代码：`CN`；
- 标准化人类食品记录：2,590 条；
- 稳定 ID：2,590 个，无重复；
- 产品名与事件日期缺失：0 条。

以上数量来自 2026-06-20 下载的 FDA `Import_Refusal_2024-present.zip`，后续官方更新会改变结果。

### 验证

- 6 项单元测试通过；
- 真实 ZIP 成功解析；
- JSONL 成功生成；
- 风险分类使用明确单词边界，避免明显子串误判。

### 已知问题

- 尚未进行完整 JSON Schema 自动验证；
- 风险规则仍是初始检索标签，不代表 FDA 官方风险分类；
- 尚未实现增量更新、质量报告和 GitHub Actions；
- 欧盟、新西兰和澳大利亚来源仍处于候选研究状态；
- 当前环境无法直接调用 `git`。

### 下一轮建议

进入 M2：先完成 schema 验证、质量报告和回归 fixture，再配置自动更新。

---

## 2026-06-20 · Round 0 · 项目背景与范围确认

### 输入目标

- 汇总美国、欧洲、澳大利亚、新西兰、日本、韩国、加拿大、香港和台湾等地区公布的不合格中国食品；
- 根据产地、食品分类和风险类型供用户查询；
- 以 GitHub 开源项目形式发布；
- 后续研究食品图片与信息辅助 AI；
- 项目获得反馈后考虑 iOS App。

### 初始范围决策

- 将官方监管信息聚合作为第一阶段；
- 将图片判断、肉类品种识别等高不确定性能力放入独立 Future Plan；
- 具体食品事件在录入前必须核对官方来源，不能直接将背景描述当成事实数据。
