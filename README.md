# Food Safety Watch / 食安观察

[![CI](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/ci.yml/badge.svg)](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/ci.yml)
[![Update FDA data](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/update-fda.yml/badge.svg)](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/update-fda.yml)
[![Smoke test Japan CAA source](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/smoke-japan-caa.yml/badge.svg)](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/smoke-japan-caa.yml)
[![Audit published Japan MHLW records](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/audit-japan-mhlw.yml/badge.svg)](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/audit-japan-mhlw.yml)
[![Probe Korea Food Safety source](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/probe-korea-recalls.yml/badge.svg)](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/probe-korea-recalls.yml)
[![Probe Taiwan TFDA source](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/probe-taiwan-tfda.yml/badge.svg)](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/probe-taiwan-tfda.yml)
[![Update Taiwan TFDA data](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/update-taiwan-tfda.yml/badge.svg)](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/update-taiwan-tfda.yml)
[![Probe China SAMR source](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/probe-china-samr.yml/badge.svg)](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/probe-china-samr.yml)
[![Probe EU RASFF source](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/probe-rasff.yml/badge.svg)](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/probe-rasff.yml)
[![Audit published EU RASFF records](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/audit-rasff-status.yml/badge.svg)](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/audit-rasff-status.yml)
[![Deploy static data site](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/deploy-pages.yml/badge.svg)](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/deploy-pages.yml)

一个以官方证据为核心的开源食品安全数据项目。它定期收集境外监管机构发布的进口拒绝、召回和安全警报，也研究中国境内官方抽检不合格信息；所有范围保留原始出处并转换为可区分监管语境的统一记录。

GitHub 仓库：[QinkunAry/CheckChineseFoodSafety](https://github.com/QinkunAry/CheckChineseFoodSafety)

在线数据浏览器：[qinkunary.github.io/CheckChineseFoodSafety](https://qinkunary.github.io/CheckChineseFoodSafety/)

> 本项目提供监管信息聚合，不进行医学诊断、实验室检测或“某食品一定安全/有毒”的判断。

完整产品方向见 [`PRODUCT_GOALS.md`](PRODUCT_GOALS.md)，每轮开发过程见 [`DEVELOPMENT_LOG.md`](DEVELOPMENT_LOG.md)。
各监管数据来源的授权和署名见 [`docs/DATA_ATTRIBUTION.md`](docs/DATA_ATTRIBUTION.md)。
Hosted GitHub Pages 验收标准见 [`docs/PAGES_ACCEPTANCE.md`](docs/PAGES_ACCEPTANCE.md)。

新增来源从 `prototype` 升级为 `implemented` 前，必须通过
[`docs/PROTOTYPE_TO_IMPLEMENTED_CHECKLIST.md`](docs/PROTOTYPE_TO_IMPLEMENTED_CHECKLIST.md)。

## 第一个目标是什么？

第一个目标不是 AI Agent，也不是通用 skills 平台，而是一条可重复、可审计的数据管道：

1. 从一个官方来源取得公开数据；
2. 保存来源、抓取时间和原始记录标识；
3. 转换为统一字段；
4. 用确定性规则添加食品类别和风险标签；
5. 导出 JSONL，供网页、API、分析和未来 App 使用。

MVP 先打通美国 FDA Import Refusal Report 中原产地为中国、且属于 FDA Product Code Builder 人类食品行业的记录。FDA 页面说明该数据来自 OASIS、按月更新，并提供 2002 年至今的 ZIP/CSV 文件。第一阶段只处理 `2024-present` 数据包，以缩短反馈周期。动物饲料、食品设备、仓储、药品、化妆品和医疗器械暂不纳入。

AI Agent 以后可以负责异常监控、翻译建议、分类候选和人工复核队列，但不应成为数据事实层。类似 OpenClaw 的 skills 适合在接口稳定后把“查询食安记录”“解释监管原因”等能力提供给其他 Agent。

## 快速开始

项目使用 Python 3.11+，JSON Schema 验证依赖 `jsonschema`。

```powershell
python -m pip install -e .
python -m food_safety_watch sources
python -m food_safety_watch update-fda
```

也可以解析已经下载的官方 ZIP（便于离线复现与调试）：

```powershell
python -m food_safety_watch fetch-fda --archive data/raw/fda-2024-present.zip --country CN
```

运行测试：

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

验证已有数据并生成质量报告：

```powershell
python -m food_safety_watch validate
```

生成本地静态数据浏览器：

```powershell
python -m food_safety_watch build-site --output-dir site
python -m http.server 8000 -d site
```

然后打开 <http://localhost:8000>。当前静态浏览器只读取 `implemented`
来源的正式发布数据，支持按来源、风险标签、监管动作、年份和关键词筛选。
`site/` 是生成产物，不提交入库；GitHub Pages workflow 会在 runner 上重新生成并部署。

## 数据边界

- `import_refusal` 不等于召回，也不表示同类产品全部存在风险。
- `origin_country` 在 FDA 数据中来自申报制造商所在国家/地区，不能自动推断品牌国籍或全部原料产地。
- 风险标签是便于检索的项目分类，监管机构原始原因文本始终优先。
- 中文翻译在进入事实字段前应经过人工或可追踪的审核流程。
- 不同监管系统的 source link 能力不同：有些是逐条详情页，有些只能指向官方检索页、数据集或需要入口会话的页面。
- `prototype` 来源只能生成 smoke、inventory 和 candidate artifact；只有通过发布前 checklist 后，才允许写入 `data/processed/`。

## 项目结构

```text
data/sources.json          数据源登记表
data/state/                来源增量状态（非监管事实）
data/candidates/           候选记录产物（不等于正式发布数据）
site/                      由 build-site 生成的静态数据浏览器
schemas/record.schema.json 统一记录契约
src/food_safety_watch/     采集与标准化代码
tests/                     单元测试
docs/ARCHITECTURE.md       架构和路线图
docs/DATA_ATTRIBUTION.md   监管数据授权与署名
docs/PAGES_ACCEPTANCE.md   Hosted GitHub Pages 线上验收清单
docs/PROTOTYPE_TO_IMPLEMENTED_CHECKLIST.md 来源发布前门禁
PRODUCT_GOALS.md           最终产品目标与里程碑
DEVELOPMENT_LOG.md         每轮开发记录
FUTURE_AI_PLAN.md          独立的 AI 后续计划
```

## 开发记录约定

每轮实质开发完成后，都应在 `DEVELOPMENT_LOG.md` 顶部追加本轮目标、实际改动、验证结果、问题和下一步。代码完成但日志未更新，视为该轮尚未完整交付。

## 自动更新

`.github/workflows/update-fda.yml` 每周运行一次，也支持在 GitHub Actions 页面手动触发。工作流先执行测试，再抓取候选数据；Schema、重复 ID、最小记录数和数量突降检查全部通过后，才会提交数据与质量报告。失败报告作为 Actions artifact 保留，不发布失败候选。

若更新失败，工作流会创建或更新唯一的 `[automation] FDA data update failed` Issue；后续运行恢复成功时会自动评论并关闭该 Issue。关注仓库 Issues 即可接收失败状态，历史验证数据不会因失败被覆盖。

FDA 下载器会先访问官方页面动态发现当前 ZIP，并使用同一会话下载。若 FDA 拒绝某些云端 Runner 网络，可以通过仓库变量 `FOOD_SAFETY_FDA_DOWNLOAD_URL` 指定经批准、内容相同的镜像；下载内容仍必须通过 ZIP、Schema 和数据质量检查。

`.github/workflows/deploy-pages.yml` 在 `main` 分支相关数据、源码或 workflow 变化后自动生成静态数据浏览器，并通过 GitHub Pages artifact 部署；也支持手动触发。部署前会配置 Pages、安装项目、运行全量测试、生成 `site/`，并验证 `summary.json` 与 `records.json` 的记录数一致且没有缺失的 implemented source 文件。

首次使用前，需要在 GitHub 仓库 Settings → Pages 中将 Build and deployment Source 设置为 GitHub Actions。若 `Configure GitHub Pages` 步骤报 `Get Pages site failed` / `HttpError: Not Found`，通常表示 Pages 尚未启用或 source 尚未设为 GitHub Actions；完成上述设置后重新运行 workflow 即可。项目不在 workflow 中用 PAT 自动启用 Pages，避免引入额外高权限 secret。

线上页面发布后，使用 [`docs/PAGES_ACCEPTANCE.md`](docs/PAGES_ACCEPTANCE.md) 做人工验收：确认 production URL 可访问、数据 JSON 可加载、记录数量一致、筛选器可用、官方出处可追溯，并且页面文案没有把监管记录解释成超出证据范围的安全结论。

`.github/workflows/smoke-fsanz.yml` 每周只读检查 FSANZ 官方 sitemap 和固定召回详情，验证页面证据字段，并对实际发现的中国原产记录执行统一 Schema 检查。固定样本中没有中国记录会被报告，但不再误判为站点结构故障。它不会提交或发布 FSANZ 数据；通过覆盖率评估和再利用条款检查前，该来源保持 `prototype`。

同一工作流还会把官方 sitemap 与 `data/state/fsanz_recall_urls.json` 中的 345 条基线比较，只报告新增和移除的详情 URL。该基线用于避免未来重复扫描全部历史页面，不代表 345 条记录都属于中国食品或都已进入发布数据集。

当官方 sitemap 出现新增详情 URL 时，`candidate-fsanz` 只抓取这些新增页面，生成 `data/candidates/fsanz_cn.jsonl` 和 `reports/fsanz_candidates.json` 作为 artifact。候选记录用于人工复核 parser、版权/再利用边界和数据质量；在来源状态仍为 `prototype` 时，它不会合并进正式发布数据。

`.github/workflows/smoke-cfs.yml` 每周只读检查香港 CFS Food Alerts / Allergy Alerts 年度列表和固定详情页，验证 `Issue Date`、`Food Product`、`Place of origin` 和 `Reason For Issuing Alert` 字段，并对中国原产记录执行统一 Schema 检查。CFS 当前也保持 `prototype`，不会提交或发布正式数据。

同一工作流还会把 CFS 当前年度列表与 2025 年列表中的官方详情 URL 和 `data/state/cfs_alert_urls.json` 基线比较，只报告新增和移除 URL。该基线当前覆盖 36 条 alert URL，不代表 36 条都属于中国食品或已进入正式数据集。

当 CFS 官方列表出现新增详情 URL 时，`candidate-cfs` 只抓取这些新增页面，在 runner 内生成 `data/candidates/cfs_cn.jsonl` 和 `reports/cfs_candidates.json`。在 CFS 授权边界明确前，workflow 只上传诊断报告 artifact，不上传候选 JSONL；候选记录不会自动合并进正式发布数据。

CFS 的官方版权声明要求获得食物环境卫生署事先书面授权后，才可复制、分发、传播或公开提供其版权作品。因此在授权或等效复用依据记录前，CFS 保持 `prototype`；workflow 只上传最小诊断报告，不上传包含官方原因文本的候选 JSONL。

加拿大 Recalls and Safety Alerts 当前保持 `candidate`。官方 open data 提供每日更新的 JSON/CSV/RSS，并使用 Open Government Licence - Canada；但已观察到的 open-data 字段和样本详情页没有稳定原产地字段，因此在找到明确 origin evidence 前不能发布中国来源记录。详见 `docs/SOURCE_CANADA.md`。

可用 `probe-canada-origin` 做只读抽样诊断。2026-06-24 的真实 probe 显示：33,692 条全类别记录中有 5,243 条 CFIA 食品记录，open data 中 12 条 CFIA 食品记录提到 China/Chinese；抽样 32 个详情页后，仍没有发现明确中国原产地证据。

欧盟 RASFF 已升级为 `implemented`。`probe-rasff` 已在 GitHub Actions 通过：它从 RASFF Window 官方目录动态取得国家和产品类型 ID，以 `originCountry=CN` 与 `notificationType=food` 双条件查询，并用印度人类食品作为非中国对照。`inventory-rasff` 完整扫描 13 页；2026-07-12 复核 12 个自然增量后，11 条非 FCM 食品记录已发布，1 条 `food contact materials` 被排除，baseline 更新为 1,226；2026-07-19 又复核 5 个自然增量并接受 baseline 1,231。Probe Action 仍只上传诊断报告，不自动发布监管记录。详见 `docs/SOURCE_RASFF.md`。

本地 `candidate-rasff` 默认只选择 baseline 后新增或指纹变化的 reference，也可用 `--reference` 生成小规模显式复核批次。官方 detail endpoint 已解决 search `subject` 不是产品名的问题：`2026.5752` 的真实产品是 `Vermicelli`，候选还会保留 classification、risk、basis、status、distribution、measures 和结构化 hazard。`smoke-rasff-detail` 使用两条有效中国样本与一条印度对照验证 detail 漂移。另一个样本 `2026.5575` 已被官方标记为 withdrawn，因此正式发布必须依赖 detail-status 重查规则，而不能只看 search inventory。详见 `docs/reviews/RASFF_INITIAL_CANDIDATE_REVIEW.md`。

RASFF lifecycle 采用明确状态机：`ec_validated` 映射为 `active`，`ec_withdrawn` 映射为 `withdrawn`，未知或矛盾组合映射为 `review_required`；corrigendum 本身不会撤回仍有效的通知。候选技术状态与 `lifecycle_gate_status` 分离，withdrawn 记录保留审计证据但不能通过 active 发布门禁。

RASFF explicitly reviewed release 当前包含 18 条 active reference。首批 3 条在 2026-07-01 发布；2026-07-10 已完成一次 `official_last_update` correction；2026-07-12 又发布 11 条自然增量并接受 1,226 条 inventory baseline；2026-07-14 因官方将 `2026.5888` 标记为 `ec_withdrawn`，已显式从 active release 移除，并同步更新 3 条仍 active 的 correction；2026-07-19 先处理 6 条仍 active 的官方 detail correction，随后发布 5 条新增 China-origin food reference 并接受 1,231 条 inventory baseline。`publish-rasff-reviewed` 要求人工批准列表与输入 JSONL 完全一致，执行 Schema、来源、detail 字段、生命周期、数量下降和最大批量门禁，并成对原子写入 JSONL 与含逐条 provenance、CC BY 4.0 署名及修改声明的 metadata；替换失败会回滚旧版本。

`audit-rasff-status` 以正式 JSONL 为 baseline，逐条比较官方 detail 中的生命周期、last update、产品、hazard、classification、risk、measures 和 follow-up；一致时 `passed`，合法但已变化时返回 `action_required`，网络或证据失败时返回 `failed`。每周/手动 Action 不修改数据，失败时上传报告并创建或更新维护 Issue；13 条 withdrawal/correction release 的 hosted audit 已恢复通过，18 条 reviewed release 的 hosted audit 也已通过。`docs/RASFF_OPERATIONS.md` 已被维护者接受为 RASFF 生产发布、撤回和回滚流程。

后续发布使用 `--merge-current`：未点名的既有记录保持不变，新增或更正必须逐条批准；官方确认撤回时使用 `--removal-only --remove-reference`，并受数量下降门禁保护。完整的人审、增量、撤回与 `git revert` 回滚流程见 `docs/RASFF_OPERATIONS.md`。

扩大 detail 复核现覆盖 10 条唯一记录、三类 notification、五种 risk 决策、chemical/adulteration/no-hazard、corrigendum 与 withdrawn；全部字段和 Schema 检查通过，混入 withdrawn 时 lifecycle gate 会阻塞。CC BY 4.0 复用评审也已完成：未来 release 必须保留 © European Union / European Commission / DG SANTE / RASFF 署名、来源与许可链接，明确本项目做过筛选和标准化修改，并禁止暗示官方背书。详见 `docs/reviews/RASFF_EXPANDED_DETAIL_REVIEW.md` 与 `docs/reviews/RASFF_REUSE_REVIEW.md`。

日本 CAA / MHLW 已升级为 `implemented`。`smoke-japan-caa` 每周固定检查两条中国来源样本和一条非中国对照，并要求至少 2 条 China 与 2 条 MHLW-backed 候选；CAA inventory 使用 append-only 已见 URL 集合。正式发布边界仅限带已验证 MHLW `RCL...` 详情的记录，使用 MHLW ID、详情 URL和 PDL 1.0 署名；CAA-only 表述不发布。详见 `docs/SOURCE_JAPAN.md`。

首次字段复核接受了 `RCL202601519`（中国产とんぶり瓶装，检出芽胞菌/梭菌属）并生成 1 条 MHLW-backed 正式记录及 PDL metadata。混合宫崎县产/中国产鳗鱼的 `RCL202601495` 因当前单一原产国字段会造成误导而未发布；`RCL202601408` 继续作为非中国对照。CI 验证正式 JSONL，增量、显式移除、原子回滚和 PDL provenance 均已实现。

严格 Japan candidate 与 published-detail audit workflow 均已在 GitHub Runner 通过。`audit-japan-mhlw` 会逐条重取已发布 MHLW detail，字段变化返回 `action_required`，技术/证据失败返回 `failed`；首次 hosted audit 为 1 audited、0 changed。每周/手动 Action 上传报告并维护失败 Issue。后续数据使用显式批准的 `--merge-current`，完整流程见 `docs/JAPAN_OPERATIONS.md`。

韩国 Food Safety Korea 当前保持 `candidate`。`probe-korea-recalls` 及其每周只读 GitHub Action 可无密钥检查官方召回门户列表和详情，并要求至少保留 1 条明确中国来源样本；2026-06-28 的 359 条当前记录中只有 1 条 `중국산` 产品，制造国和进口产品关联字段均为空，尚未满足升级 prototype 所需的两条中国来源门槛。官方 `I0490` OpenAPI 可申请认证 key，正式自动化前需确定生产访问方式。详见 `docs/SOURCE_KOREA.md`。

台湾 TFDA 已升级为 `implemented`。官方不符合食品 JSON 直接提供产地、产品、原因、处置与日期；首次正式发布从 2,472 条官方记录中生成 388 条中国来源食品及食品添加物记录。`update-taiwan-tfda` 每次重建完整快照，通过生产门禁后原子替换 `data/processed/taiwan_tfda_cn.jsonl`，并同步发布署名 metadata 与质量报告。详见 `docs/SOURCE_TAIWAN.md` 和首次候选复核记录 `docs/reviews/TAIWAN_TFDA_INITIAL_CANDIDATE_REVIEW.md`。

台湾生产发布命令 `update-taiwan-tfda` 每次重建完整快照，并在通过来源数量、发布数量、数量突降、Schema、重复 ID、解析错误及未分类风险门禁后原子替换正式文件。独立的 `Update Taiwan TFDA data` Action 负责提交通过验证的数据、保存质量报告，并通过唯一 Issue 报告失败。首次生产 Action 已在提交 `21e8d22` 完成 388 条记录的正式发布。

中国大陆 SAMR 国家级食品安全监督抽检当前为 `candidate`。只读 `probe-china-samr` 验证公告和 XLSX/ZIP 核心字段；`inventory-china-samr` 用 3 页完整扫描与 78 条公告 URL baseline 比较增删；二者组成的扩展 Action 已在 GitHub Runner 通过。手动 `candidate-china-samr` 可在本地把 73 个物理行按抽样编号聚合成 46 个事件，处理延续行和 Excel 日期并通过统一 Schema，但不会加入定时 workflow 或上传候选 artifact。SAMR 是中国市场监管范围，不是原产地数据集：候选记录使用 `regulatory_scope: domestic_market`、`market_country: CN` 和 `origin_country: unknown`，不能根据生产商、进口商或代理地址推断来源国。版权和标准化复用依据明确前不发布候选或正式数据。详见 `docs/SOURCE_CHINA_SAMR.md` 和首次本地复核 `docs/reviews/CHINA_SAMR_INITIAL_CANDIDATE_REVIEW.md`。

## 路线图

- [x] 确定 evidence-first 数据模型
- [x] 建立 FDA CSV 下载与标准化适配器
- [x] 验证 FDA 实际数据并加入回归样本
- [x] 增加 Schema 验证、去重检查、数量突降保护和质量报告
- [x] 增加 GitHub Actions 测试与每周自动更新
- [x] 增加 FDA 更新失败通知
- [x] 增加来源级 URL 增量监控
- [x] 将香港 CFS 从 smoke prototype 推进到 candidate 管线
- [x] 将日本 CAA / MHLW 推进到 smoke、inventory 与 candidate 管线
- [x] 将日本 CAA / MHLW 升级为 implemented 正式数据源
- [x] 完成韩国 Food Safety Korea 来源 probe 与原产地证据评估
- [x] 将台湾 TFDA 边境不合格食品推进到只读 probe prototype
- [x] 为台湾 TFDA 增加增量记录基线与候选 JSONL 管线
- [x] 将台湾 TFDA 升级为 implemented 正式数据源
- [x] 完成中国大陆 SAMR 公告与 XLSX/ZIP 只读 source probe
- [x] 为中国大陆 SAMR 建立完整分页与 78 条公告 URL baseline
- [x] 为中国大陆 SAMR 实现抽样编号聚合和本地候选复核
- [x] 打通欧盟 RASFF 官方公开 JSON 探针与 China+food 双过滤
- [x] 为欧盟 RASFF 建立完整分页与 1,214 条指纹 baseline
- [x] 为欧盟 RASFF 增加本地增量候选与首次字段复核
- [x] 接入欧盟 RASFF 官方 detail 产品、hazard 与监管状态
- [x] 实现欧盟 RASFF 已发布记录 detail-status 审计框架
- [x] 完成欧盟 RASFF 扩大 detail 样本与 CC BY 4.0 署名评审
- [x] 发布首批 3 条人工批准 RASFF 数据与逐条 provenance metadata
- [x] 发布欧盟 RASFF 11 条真实增量并将完整 baseline 更新至 1,226
- [x] 将欧盟 RASFF 升级为 implemented 正式数据源
- [x] 生成本地静态数据页与筛选界面
- [x] 增加 GitHub Pages 静态站点部署 workflow
- [x] 完成首次 hosted GitHub Pages 部署验收
- [x] 增加 hosted GitHub Pages 线上验收清单与公开入口说明
- [x] 增加静态浏览器来源解释、风险标签说明和阅读边界提示
- [x] 增加静态浏览器中英界面切换
- [x] 增加当前筛选下的高频食品类别 × 风险标签摘要
- [x] 增加静态浏览器记录详情展开
- [x] 区分官方详情链接、检索入口和可能需要会话的 source link
- [ ] 按可获取性接入加拿大、韩国、新西兰等剩余来源
- [ ] 在事实层稳定后提供 API / Agent skill
- [ ] 评估 iOS App

## 许可证

代码采用 MIT License。监管数据本身的再利用条件以各来源机构条款为准；发布数据快照前需逐项核对。
