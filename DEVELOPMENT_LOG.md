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

## 2026-09-02 · Round 71 · Static browser evidence guide cards

### 本轮目标

继续制作产品层页面，让 hosted GitHub Pages 不只是数据列表，也能帮助普通用户理解来源、风险标签和监管动作边界。

### 已完成内容

- 静态浏览器新增“阅读边界”提示，明确记录代表具体监管事件，不等于某类食品整体安全或不安全；
- 新增来源说明卡片，解释 FDA、Taiwan TFDA、Japan MHLW-backed 和 EU RASFF 的监管语境；
- 新增风险标签说明卡片，解释 chemical、microbiological、labeling、adulteration 等标签含义；
- 新增措施类型说明卡片，解释 import refusal、inspection failure、RASFF notification 和 recall 的差异；
- 增加静态页面回归测试，防止公开说明组件被意外移除；
- README 路线图记录该产品体验改进。

### 决策

这轮继续保持无前端框架、无构建依赖的纯静态页面。产品层先解决“用户能不能正确读懂数据”，再考虑更复杂的可视化、中文/英文切换或 AI 查询。

### 下一步

提交并部署后，在线上页面检查说明卡片是否显示正常。下一轮可以继续做中英界面切换，或做“高风险食品聚合”摘要模块。

---

## 2026-09-02 · Round 70 · Public site entry and acceptance checklist

### 本轮目标

把首次通过的 hosted GitHub Pages 部署沉淀为公开产品入口和可重复验收流程。

### 已完成内容

- README 顶部新增在线数据浏览器入口：`https://qinkunary.github.io/CheckChineseFoodSafety/`；
- README 增加 hosted Pages 验收文档链接；
- 新增 `docs/PAGES_ACCEPTANCE.md`，覆盖部署前检查、页面可访问性、数据完整性、筛选体验、官方证据、授权署名、失败处理和人工验收标准；
- README 项目结构和路线图同步记录该验收清单。

### 决策

Hosted Pages 是当前项目的第一个公开产品入口；后续页面体验优化必须继续服从 evidence-first 边界，不能把进口拒绝、召回、边境不合格或 RASFF notification 解释成超出官方证据范围的食品安全结论。

### 下一步

提交文档后，可以按 `docs/PAGES_ACCEPTANCE.md` 对线上页面做一次人工抽样验收。若验收通过，下一轮建议进入 UI 产品体验改进：来源解释、风险标签说明、中英显示切换或高风险食品聚合。

---

## 2026-09-02 · Round 69 · Hosted GitHub Pages deployment accepted

### 本轮目标

记录 `Deploy static data site` workflow 首次 hosted GitHub Pages 部署通过。

### 验收结果

维护者已确认 workflow 通过。此前的阻塞点已经闭环：

- 仓库已改为 public，使 GitHub Pages 可用于该开源项目；
- Settings → Pages 已切换为 GitHub Actions source；
- `configure-pages` first-run 404 已消失；
- Pages artifact upload 与 deploy action 已升级到 Node.js 24 兼容版本；
- 静态数据浏览器可由 GitHub Actions 自动构建和部署。

### 已完成内容

- README 路线图中“完成首次 hosted GitHub Pages 部署验收”改为完成；
- 将 GitHub Pages 从待验收能力转为已验收产品入口。

### 下一步

进入产品层下一轮：优先做线上页面验收清单与公开入口说明，然后再决定继续优化静态浏览器体验，或转向未 implemented 来源的生产化。

---

## 2026-09-02 · Round 68 · GitHub Pages Node 24 action upgrade

### 本轮目标

处理 `Deploy static data site` workflow 已可运行后剩余的 Node.js 20 deprecation warnings。

### 诊断

Pages 404 已由仓库改为 public 并在 Settings → Pages 中启用 GitHub Actions source 解决。新的 annotations 是 warning，不是 failure：`actions/upload-pages-artifact@v4` 内部仍触发 Node.js 20 相关提示，`actions/deploy-pages@v4` 也提示即将迁移到 Node.js 24。

### 已完成内容

- 将 `actions/upload-pages-artifact` 从 `v4` 升级到 `v5`；
- 将 `actions/deploy-pages` 从 `v4` 升级到 `v5`；
- 保持 build/test/site verification 流程不变，只更新 Pages 官方 action runtime。

### 下一步

提交并推送后重新运行 `Deploy static data site`。若 workflow 通过且不再出现 Node.js 20 annotations，即可进行首次 hosted Pages 访问验收，并把 README 路线图中的 hosted Pages 部署验收改为完成。

---

## 2026-09-01 · Round 67 · GitHub Pages first-run 404 fix

### 本轮目标

处理 `Deploy static data site` workflow 在 `Configure GitHub Pages` 步骤失败的问题：`Get Pages site failed` / `HttpError: Not Found`。

### 诊断

失败发生在 Pages 配置阶段，而不是数据构建阶段。根据 GitHub Pages custom workflow 与 `actions/configure-pages` action 定义，custom workflow 首次使用前必须先在仓库 Settings → Pages 中将 Build and deployment Source 设为 GitHub Actions。`configure-pages` 的 `enablement` 参数可以尝试启用 Pages，但需要非默认 `GITHUB_TOKEN` 的额外高权限 token，因此本项目不在 workflow 中自动启用。

### 已完成内容

- 将 `actions/configure-pages` 从 `v5` 升级到 `v6`，避免 Node.js 20 deprecation warning；
- 将 `Configure GitHub Pages` 步骤提前到 checkout 后，使未启用 Pages 时更早失败；
- README 增加 `Get Pages site failed` / `HttpError: Not Found` 的处理说明；
- 明确不使用 PAT 自动启用 Pages，避免引入额外高权限 secret。

### 下一步

维护者需要在 GitHub 仓库 Settings → Pages 中选择 Source: GitHub Actions，然后重新运行 `Deploy static data site`。若仍失败，再根据新的 deploy job 日志处理权限或 environment 问题。

---

## 2026-08-31 · Round 66 · GitHub Pages deployment workflow

### 本轮目标

继续产品层工作：在本地静态数据浏览器 MVP 之后，增加 GitHub Pages 自动部署 workflow，让正式发布数据可以被构建成在线静态站点。

### 已完成内容

- 新增 `.github/workflows/deploy-pages.yml`；
- workflow 在 `main` 相关数据、源码或部署配置变化时运行，也支持手动触发；
- build job 会 checkout、安装 Python 项目、运行全量单元测试、执行 `build-site --output-dir site`；
- build job 验证 `site/index.html`、`site/data/records.json` 与 `site/data/summary.json` 存在，且 summary 记录数与 records JSON 一致；
- 使用 GitHub Pages 官方 artifact 部署链路：`configure-pages`、`upload-pages-artifact`、`deploy-pages`；
- 将 `site/` 加入 `.gitignore`，把静态站点作为生成产物而不是 committed artifact；
- README 增加 Pages workflow badge、部署说明和首次启用 Pages source 的提示。

### 决策

不提交生成后的 `site/` 目录。原因是当前 `records.json` 已接近 2.9MB，后续每次数据更新都会产生大体积 generated diff；由 GitHub Actions 从 committed `data/processed/` 重新生成并部署，更适合维护。

### 验证结果

本轮仍需最终运行全量测试、`build-site` 和 `git diff --check`。首次 hosted Pages 部署需要提交推送后，在 GitHub Actions 中验收。

### 下一步

推送后在 GitHub 仓库 Settings → Pages 中确认 Build and deployment source 为 GitHub Actions，然后运行 `Deploy static data site`。如果部署通过，下一轮记录 hosted URL，并把路线图中的 hosted Pages 验收项勾选。

---

## 2026-08-12 · Round 65 · Static data browser MVP

### 本轮目标

在 FDA、Taiwan TFDA、Japan MHLW 与 EU RASFF 进入 `implemented` 后，启动产品层第一步：把正式发布数据生成一个本地可浏览、可筛选的静态页面。

### 已完成内容

- 新增 `food_safety_watch.static_site`，从 `data/sources.json` 中筛选 `implemented` 来源；
- 默认读取 4 个正式发布文件：FDA、Taiwan TFDA、Japan MHLW、EU RASFF；
- 新增 CLI：`python -m food_safety_watch build-site --output-dir site`；
- 生成 `site/index.html`、`site/data/records.json`、`site/data/summary.json` 和 `site/README.md`；
- 静态页面支持关键词、来源、hazard tag、action type 和年份筛选；
- README 增加本地静态站点生成与预览命令；
- 路线图将“静态数据页与筛选界面”拆分为本地生成已完成、GitHub Pages 部署待完成。

### 数据范围

本轮生成的静态站点使用当前 committed processed 数据，共 3,100 条正式记录：

- FDA import refusals：2,690 条；
- Taiwan TFDA inspection failures：391 条；
- EU RASFF notifications：18 条；
- Japan MHLW-backed recall：1 条。

日期范围为 2023-01-03 至 2026-07-17。页面只包含 `implemented` 来源，不包含 FSANZ、CFS、Korea、Canada、SAMR 或 New Zealand 的 prototype/candidate 数据。

### 验证结果

- `python -m unittest tests.test_static_site -v`：3 tests passed；
- `python -m food_safety_watch build-site --output-dir site`：成功生成 3,100 条记录；
- 后续需要运行全量测试与 `git diff --check` 后提交。

### 下一步

提交当前 RASFF implemented 状态与 static browser MVP。下一轮优先接 GitHub Pages / Pages Action，让 `site/` 能在线访问；随后再迭代 UI 的产品体验，例如高风险食品聚合、来源解释、风险标签说明和中文/英文显示切换。

---

## 2026-07-19 · Round 64 · EU RASFF upgraded to implemented

### 本轮目标

维护者明确表示“我接受 RASFF_OPERATIONS.md”。据此完成 EU RASFF 从 `prototype` 到 `implemented` 的最终状态升级。

### 已完成内容

- 将 `docs/RASFF_OPERATIONS.md` 状态改为 accepted for implemented source operations；
- 将 `data/sources.json` 中 `eu_rasff` 从 `prototype` 改为 `implemented`；
- 更新 `docs/SOURCE_RASFF.md` 的 Decision、reuse review 与 implemented gate 说明；
- 更新 README，将 RASFF 描述改为 implemented，并把 RASFF implemented 路线图项勾选；
- 更新 `docs/PROTOTYPE_TO_IMPLEMENTED_CHECKLIST.md`，标记 EU RASFF 为 `implemented`。

### 验收依据

- 官方 public JSON probe、完整 inventory、detail smoke、候选复核、正式发布、metadata attribution、发布后 detail-status audit、active correction、自然增量、withdrawn removal、baseline acceptance 和 GitHub hosted audit 均已完成；
- 当前 release 为 18 条 explicitly reviewed active RASFF records；
- 当前 accepted inventory baseline 为 1,231 条 China-origin food-query references；
- 维护者已接受 RASFF 发布、撤回与回滚 runbook。

### 下一步

RASFF 进入维护模式。后续重点转向产品层：静态数据页/筛选界面、统一数据浏览体验，以及未实现来源中最有价值的下一批生产化目标。

---

## 2026-07-19 · Round 63 · RASFF 18-record hosted audit accepted

### 本轮目标

记录维护者确认 GitHub Actions `Audit published EU RASFF records` 已对 18 条 RASFF release 通过，并同步修正状态文档中的旧阻塞描述。

### 已完成内容

- 确认当前 `main` / `origin/main` 为 `290d6a9 data: publish reviewed RASFF increment`；
- 本地工作区在检查前为 clean；
- 将 RASFF 顶层说明从 13 条 release / 1,226 baseline 更新为 18 条 release / 1,231 baseline；
- 将 `prototype -> implemented` checklist 中的 RASFF 阻塞项更新为：18-record hosted audit 已通过，仍需维护者接受 `RASFF_OPERATIONS.md`；
- 将 README 与 `data/sources.json` 的 RASFF 状态说明从“等待 hosted audit”更新为“hosted audit 已通过，等待 operations 接受”。

### 决策

RASFF 仍暂留 `prototype`，不在本轮自动升级为 `implemented`。最后剩余门槛是维护者明确接受 `docs/RASFF_OPERATIONS.md` 作为生产发布、撤回和回滚流程。

### 下一步

若维护者接受 `RASFF_OPERATIONS.md`，下一轮即可把 `eu_rasff` 从 `prototype` 升级为 `implemented`，并同步更新 README、source assessment、checklist 和 development log。

---

## 2026-07-19 · Round 62 · RASFF reviewed natural increment release

### 本轮目标

在 13 条 RASFF release 的 hosted audit 恢复通过后，处理上一轮刻意暂缓的 search inventory 增量：5 个 new reference 与 1 个 changed search fingerprint。

### 候选结果

重新运行 fresh `candidate-rasff`，结果为 baseline 1,226、current 1,231、5 new、1 changed、6 candidates。

- `2026.5595`：既有记录，search fingerprint changed；detail 已是上一轮 correction 后的 active 版本；
- `2026.6208`：Matcha powder，农药残留，border rejection；
- `2026.6214`：Rice flour，未经授权 genetically modified，border rejection；
- `2026.6241`：Green Tea，高氯酸盐，information notification；
- `2026.6278`：Cooking Wine，health certificate 不合格，border rejection；
- `2026.6384`：herbal drink，novel food，border rejection。

6 条均为 China-origin human food、`record_status: active`、official status `ec_validated`；candidate report 为 0 blockers、0 Schema errors、lifecycle gate passed。

### 处理方式

- 使用 `publish-rasff-reviewed --merge-current` 显式批准 6 个 reference；
- RASFF formally reviewed active release 从 13 条扩展到 18 条；
- metadata 记录本批 approved references 与逐条 provenance，`removed_references` 为空；
- 在发布后本地 audit 通过的前提下，使用 `inventory-rasff --accept-current` 接受当前完整 inventory baseline；
- RASFF accepted inventory baseline 从 1,226 更新为 1,231。

### 验证结果

- `publish-rasff-reviewed` quality gate passed；
- 发布后 `audit-rasff-status`：passed，18 audited、0 changed；
- inventory accept-current 完成，state `record_count` 为 1,231。

### 下一步

提交并推送后重新运行 hosted `Audit published EU RASFF records`，确认 18 条 release 在 GitHub runner 上也通过。RASFF 暂不升级为 `implemented`：仍需 hosted audit 验收本轮 18 条 release，并由维护者接受 `docs/RASFF_OPERATIONS.md` 的发布/回滚流程。

---

## 2026-07-19 · Round 61 · RASFF active correction batch

### 本轮目标

处理 GitHub Actions `Audit published EU RASFF records` 返回的 13 条 release 中 6 条 `action_required`，确认是否有撤回或只需 active correction。

### 触发结果

本地复现 hosted audit：published 13、audited 13、changed 6。

- `2026.5595`：仍 active，`reasons`、`official_hazards`、`official_measures` 与 `official_last_update` 变化；
- `2026.5922`：仍 active，`official_last_update` 与 follow-up 变化；
- `2026.5938`：仍 active，`official_last_update` 与 follow-up 变化；
- `2026.6040`：仍 active，`official_last_update` 与 follow-up 变化；
- `2026.6070`：仍 active，`official_last_update` 与 follow-up 变化；
- `2026.6185`：仍 active，`official_last_update` 与 follow-up 变化。

### 处理方式

- 为 6 条 reference 生成 explicit candidate；
- candidate 结果：6 candidates、0 blockers、0 Schema errors、lifecycle gate passed；
- 6 条均为 `active` / `ec_validated`，没有 withdrawn removal；
- 使用 `publish-rasff-reviewed --merge-current` 批准 6 条 correction；
- 正式 RASFF release 保持 13 条 active records；
- metadata 记录本批 6 条 approved references，`removed_references` 为空。

### 验证结果

- 发布后重跑 `audit-rasff-status`：passed，13 audited、0 changed；
- candidate 同时提示当前 search inventory 存在 5 个 new reference 与 1 个 changed search fingerprint；这些不是本轮 published audit 修复范围，未发布、未接受 baseline。

### 下一步

提交并推送后重新运行 hosted `Audit published EU RASFF records`。若通过，再单独处理当前 search inventory 的 5 个 new 与 1 个 changed candidate review；不要在 hosted audit 通过前接受新的 inventory baseline。

---

## 2026-07-14 · Round 60 · RASFF withdrawal removal rehearsal

### 本轮目标

在准备把 EU RASFF 升级为 `implemented` 前，重新核查 14 条正式记录的 detail-status，并确认 operations 文档是否覆盖真实维护场景。

### 触发结果

本地在线 `audit-rasff-status` 返回 `action_required`：

- published 14、audited 14；
- changed 4；
- `2026.5595`：仍 active，`official_last_update` 与 follow-up/measures 变化；
- `2026.5888`：从 active 变为 `ec_withdrawn` / project `withdrawn`；
- `2026.5922`：仍 active，`official_last_update` 与 measures 变化；
- `2026.6070`：仍 active，`official_last_update`、measures 与 follow-up 变化。

### 处理方式

- 为 4 条 reference 生成 explicit candidate，确认 lifecycle counts 为 active 3、withdrawn 1；
- 没有把 withdrawn candidate 发布为 active 记录；
- 为 `2026.5595`、`2026.5922`、`2026.6070` 生成 active correction candidate；
- 使用 `publish-rasff-reviewed --merge-current` 批准 3 条 correction，同时 `--remove-reference 2026.5888`；
- 正式 RASFF release 从 14 条 active records 变为 13 条；
- metadata 记录本批 approved references 与 removed reference。

### 验证结果

- 发布后重跑 `audit-rasff-status`：passed，13 audited、0 changed；
- RASFF 专项测试 60 tests passed；
- `probe-rasff` 与 `inventory-rasff` 在同轮检查中分别通过：1,226 China-origin food notifications，inventory unchanged。

### 决策

RASFF 已完成三类真实维护演练：active correction、natural increment、withdrawn removal。由于本轮 13 条 release 还需要 GitHub hosted audit 验收，`eu_rasff` 仍暂留 `prototype`；如果 hosted audit 通过且维护者接受 `RASFF_OPERATIONS.md`，下一轮即可升级为 `implemented`。

---

## 2026-07-12 · Round 59 · RASFF configuration portal-link drift

### 触发结果

GitHub Actions `Probe EU RASFF source` 失败，CLI 摘要显示 `0 China-origin food notifications`。本地复现后发现实际失败点不是 search API 返回 0，而是 `parse_configuration` 拒绝了官方 public configuration 中新的 `openPortalLink`。

### 原因

RASFF public configuration 当前返回：

`https://developer.datalake.sante.service.ec.europa.eu/api-details#api=2955fdc1-9da2-4927-977f-40dc50db1128&operation=cc6aab62-bd15-4904-b20d-54551ccb9468`

旧代码只接受 data.europa 的 `restored_rasff` dataset URL。官方 search、country catalog、product-type catalog 和完整 inventory 仍然正常；本地 `inventory-rasff` 回查仍为 1,226 current、0 new、0 removed、0 changed。

### 修复

- `parse_configuration` 现在接受两种官方 portal link：
  - `data.europa.eu` 上的 `restored_rasff` dataset；
  - `developer.datalake.sante.service.ec.europa.eu/api-details#api=...`；
- 新增单元测试覆盖 data.europa 与 DG SANTE developer portal 两种 configuration；
- `probe-rasff` CLI 在失败时额外打印第一条 blocker，避免 future logs 只显示 `0 notifications` 而隐藏真正原因。

### 验证

- `probe-rasff` 在线恢复通过：1,226 China-origin food notifications、10 normalized samples；
- `tests.test_rasff_probe` 11 tests passed。

### 下一步

提交并推送后重新运行 `Probe EU RASFF source`。预期 probe 阶段恢复绿色；若后续 inventory 或 detail smoke 失败，再按对应 report 单独处理。

---

## 2026-07-12 · Round 58 · RASFF reviewed increment release and baseline acceptance

### 本轮目标

继续处理 EU RASFF 自然增量：重新扫描当前官方 inventory，排除不属于食品记录的 FCM，复核可发布候选，发布增量并更新 baseline。

### 在线扫描结果

- `inventory-rasff` 当前完整扫描：baseline 1,214，current 1,226；
- 新增 reference 12 个，removed 0，changed 0；
- 新增 reference 为 `2026.5595`、`2026.5818`、`2026.5869`、`2026.5888`、`2026.5922`、`2026.5933`、`2026.5938`、`2026.5947`、`2026.6040`、`2026.6070`、`2026.6159`、`2026.6185`。

### 候选复核

- 自然 candidate 对 12 个新增 reference 失败关闭：11 candidates、1 parse blocker；
- blocker 为 `2026.5818`，detail category 是 `food contact materials`，继续按 out-of-scope 排除；
- 对剩余 11 个 reference 执行 explicit review：11 selected、11 candidates、0 blockers、0 Schema errors、lifecycle gate passed；
- 11 条均为 `active` / `ec_validated`，中国 ORIGIN 明确，source URL 均为官方 RASFF notification route；
- 分类覆盖 herbs/spices、food additives、meat、tea、fruit、cereals/bakery、nuts、food supplements、confectionery；
- hazard tags：chemical 7，other/unclassified 4。

### 发布与 baseline

- 使用 `publish-rasff-reviewed --merge-current` 发布 11 条增量；
- 正式 RASFF release 从 3 条增至 14 条；
- 本批 approved references 记录在 metadata，完整 release references 保留 14 条；
- 发布后 `audit-rasff-status` 在线通过：14 audited、0 changed；
- 执行 `inventory-rasff --accept-current` 接受当前 1,226 条官方 search baseline；
- baseline 接受后普通 inventory 回查为 unchanged：current 1,226、new 0、removed 0、changed 0。

### 下一步

提交并推送后运行 GitHub Actions：

- `Audit published EU RASFF records` 应审计 14 条并通过；
- `Probe EU RASFF source` 应显示 inventory unchanged，除非官方又发生新变动。

若 hosted audit 通过，RASFF 已完成真实增量与 correction 维护演练；下一步可以决定是否把 `eu_rasff` 从 `prototype` 升级为 `implemented`。

---

## 2026-07-10 · Round 57 · RASFF published audit correction

### 触发结果

GitHub Actions `Audit published EU RASFF records` 返回 `action_required`：

- published 3、audited 3；
- changed 1；
- changed reference: `2026.5752`；
- changed field: `official_last_update`；
- previous: `29-06-2026 17:15:21`；
- current: `09-07-2026 14:50:36`；
- record status remained `active`。

### 处理方式

- 本地复现 hosted audit，确认不是网络错误或代码异常；
- 通过 `candidate-rasff --reference 2026.5752` 重新抓取官方 detail；
- candidate 通过：1 selected、1 candidate、0 blockers、0 Schema errors、lifecycle gate passed；
- 字段比对显示只有 `official_last_update` 与 candidate `retrieved_at` 变化，产品、原因、hazard、状态、source URL 均未变化；
- 使用 `publish-rasff-reviewed --merge-current --approved-reference 2026.5752` 原子重建 RASFF release；
- 正式 release 仍为 3 条，`release_references` 不变；同 reference correction 保留首次 `retrieved_at`。

### 验证结果

- correction 发布后重跑 `audit-rasff-status`：passed，3 audited、0 changed；
- `2026.5752` 正式记录的 `official_last_update` 已更新为 `09-07-2026 14:50:36`；
- `2026.5752` 的 `retrieved_at` 仍保留初次发布时间 `2026-07-01T13:27:56.057826+00:00`。

### 额外观察

同一次 live inventory 观察到当前 RASFF China-origin food query 已从前一轮 1,223 增至 1,224，新 reference 增至 10。此信息只作为增量提示；本轮只处理 published audit 指出的已发布记录 correction，没有发布新的未复核增量。

### 下一步

提交本次 correction 后重新运行 GitHub Actions 的 `Audit published EU RASFF records`。若通过，再回到 RASFF 8/9 个自然增量的人工复核与增量发布计划。

---

## 2026-07-09 · Round 56 · RASFF natural increment test and FCM boundary

### 本轮目标

对 EU RASFF 做一次真实在线测试，确认 published audit、public API probe、detail smoke、complete inventory 和自然增量 candidate 是否仍可用。

### 验证结果

- RASFF 专项单元测试通过：58 tests；
- `audit-rasff-status` 本地沙箱内因代理连接失败，沙箱外重跑通过：3 audited、0 changed；
- `probe-rasff` 在线通过：当前 China-origin human-food query 返回 1,223 条，10 normalized samples；
- `smoke-rasff-detail` 在线通过：2 个中国 detail、1 个 India control、1 个 hazard sample；
- `inventory-rasff` 在线通过并发现自然增量：baseline 1,214，current 1,223，new 9，removed 0，changed 0；
- 修正前 `candidate-rasff` 生成 9 条候选，技术解析、Schema 和 lifecycle gate 均通过；
- 加入 FCM 排除规则后，自然 candidate 对 9 个 new reference 失败关闭：8 candidates、1 parse blocker，blocker 为 `2026.5818` out-of-scope；
- 排除 `2026.5818` 后的 explicit review 通过：8 selected、8 candidates、0 blockers、0 Schema errors、lifecycle gate passed。

### 新发现的问题与决策

自然增量中 `2026.5818` 的 detail `product_category` 为 `food contact materials`。虽然它出现在 RASFF food product-type query 中，但项目面向食品记录，不应把食品接触材料发布为食品安全记录。

已新增 detail-level 排除规则：`product_type == food` 和中国 ORIGIN 仍是必要条件，同时 `product_category == food contact materials` 时不归一化为食品记录。这样 search/inventory 可以继续记录官方返回的 reference，但候选发布前会把 FCM 排除在正式食品数据外。当前剩余 8 个 explicit review 候选产品覆盖 herbs/spices、food additives、meat、tea、fruit、cereal/bakery、nuts 和 food supplements。

### 代码与文档变更

- `rasff_detail.is_china_food_detail` 排除官方 detail category `food contact materials`；
- 增加 RASFF detail 单元测试，确保 FCM 不会生成 normalized record；
- `SOURCE_RASFF.md` 记录 2026-07-09 在线测试结果、9 个自然增量和 FCM 边界决策。

### 下一步

下一步可以人工复核这 8 个 explicit review 候选；若接受，则用 `publish-rasff-reviewed --merge-current` 发布增量，并在发布后更新/接受 RASFF inventory baseline。

---

## 2026-07-07 · Round 55 · Japan upgraded to implemented

### Hosted acceptance result

维护者提供 `Audit published Japan MHLW records` 的 GitHub Runner 报告：

- `status: passed`；
- published 1、audited 1、changed 0；
- `blocking_errors: []`、`change_samples: []`、`warnings: []`；
- `RCL202601519` 当前官方 MHLW detail 与正式 release 的全部审计字段一致。

这完成了 Japan 最后一个 hosted 门禁。此前严格 candidate workflow 已通过 2 China records、2 MHLW-backed records、0 Schema errors；首批字段人工复核、PDL 1.0 reuse decision、正式 JSONL/metadata、CI、在线 audit、失败 Issue、增量/显式移除、append-only inventory 与回滚流程均已完成。

### 状态升级

- `data/sources.json`：`jp_caa_recalls` 从 `prototype` 升级为 `implemented`；
- checklist 将 Japan 标记为 `implemented`；
- `JAPAN_OPERATIONS.md` 标记为已接受的正式运维流程；
- README 增加 Japan audit badge，并同步正式来源状态；
- `SOURCE_JAPAN.md` 清理旧 prototype/blocker 表述，保留 mixed-origin、CAA-only rights 和 MHLW discovery 等真实限制。

### 持续约束

- 只有 MHLW 自身明确给出中国来源证据的记录才能发布；
- CAA-only 表述和 mixed-origin notice 不进入当前正式数据；
- CAA URL 离开滚动列表不等于撤回；
- 官方字段变化必须经过 `action_required` 人工复核与原子重建，不能由 audit 自动修改；
- 每次增量仍需显式批准 reference、质量门禁和 hosted audit。

### 下一步

Japan 进入维护模式。下一开发重点应从继续扩展 Japan 转向下一个最接近 implemented 的来源，优先比较 EU RASFF 的真实增量验收与 FSANZ 的 reuse/首批候选门禁。

---

## 2026-07-07 · Round 54 · Japan strict gate acceptance, published audit and operations

### 触发结果

维护者提供最新 GitHub Runner 报告。严格门禁完整通过：smoke `status: passed`、2 China-origin pages、3 MHLW references、0 blockers；candidate `status: passed`、3 selected URLs、2 China records、2 MHLW-backed records、minimums 均为 2、0 Schema errors，非中国对照保持 `parsed_non_china`。

### Published-detail audit

- 抽取 `normalize_mhlw_detail`，candidate 与 audit 使用同一 MHLW-only 标准化路径，避免规则漂移；
- 新增 `audit-japan-mhlw`，逐条比较 event date、origin evidence、product/category、reasons、hazard tags、authority 与 source URL；
- unchanged 返回 `passed`；合法官方字段变化或中国来源证据消失返回 `action_required`；网络、ID、authority 或 URL 失败返回 `failed`；
- audit 只报告，不直接改写 release；
- 2026-07-07 在线重查 `RCL202601519`：1 audited、0 changed、`passed`；
- 新增每周/手动 `audit-japan-mhlw.yml`，始终上传报告，失败/变化时创建或更新 Issue，恢复后关闭 Issue。

### 增量与撤回语义

- `publish-japan-reviewed --merge-current` 只新增或替换本批显式批准 reference，未点名的正式记录保持不变；
- 同 reference correction 保留首次 `retrieved_at`；
- `--removal-only --remove-reference` 只允许显式删除已经发布的 MHLW reference；未知删除和批准/删除冲突失败关闭；
- 如果最后一条记录经官方更正后必须移除，可明确使用 `--min-records 0` 生成合法空 release；空 release audit 为 passed + warning；
- metadata 新增 release mode、完整 release references、本批批准和 removed references；
- 新建 `JAPAN_OPERATIONS.md`，记录新增、更正、来源证据消失、回滚与人工验收步骤。

### Inventory 语义修正

Runner 报告显示 CAA current list 从 baseline 321 变化为 current 322，并出现大量 new/removed URL。该列表会滚动，离开 current list 不等于撤回。

- Japan URL state 改为 append-only “历史已见集合”；
- `--accept-current` 写入 previous ∪ current，只追加新 URL，不丢弃旧 URL；
- inventory 的 removed 字段明确改为 `previously_seen_but_not_currently_listed`；
- 不因 URL 离开 CAA 当前列表而删除正式 MHLW 记录，正式变更只由 MHLW detail audit 决定。

### 验证与状态

- 新增 audit 测试覆盖 unchanged、产品修订、origin evidence 消失、网络失败、错误 URL、空/超限 release；
- 新增增量测试覆盖批准新增、更正时间保留、显式删除、未知/冲突删除和空 release；
- 新增 append-only seen-URL inventory 测试；
- 全套 218 项单元测试通过；
- Japan 仍为 `prototype`，等待新 audit Action 的第一次 hosted pass 和维护者接受操作手册。

### 下一步

提交后运行 CI 与 `Audit published Japan MHLW records`。若 hosted audit 为 `passed / 1 audited / 0 changed`，审核 `JAPAN_OPERATIONS.md` 后即可评估 Japan 升级为 `implemented`。

---

## 2026-07-05 · Round 53 · Japan field review and first MHLW-backed release

### 触发结果

维护者确认更新后的 `Smoke test Japan CAA source` 通过。由于当前环境无法匿名读取仓库的 Actions artifact，随后直接重新下载 3 个官方 CAA 页面与其 3 个 MHLW detail，使用项目 parser 完成字段级复核。

### 人工复核结论

- `RCL202601495`：同一 notice 同时覆盖宫崎县产鳗鱼和中国产鳗鱼；当前 schema 只有单一 `origin_country`，把整条记录标成 CN 会误导，因此不进入首批 release；
- `RCL202601519`：`とんぶり瓶詰（中国産）`，MHLW product 和 detail 明确给出中国产证据，event date 为 2026-06-12，原因是异味调查检出芽胞菌（クロストリジウム属菌），接受发布；
- `RCL202601408`：乌冬/凉面，没有中国来源证据，正确排除；
- MHLW `RCL202601519` 同时写有 `輸入食品：いいえ`，项目不据此推断供应链，只记录其产品字段明确写出的 `中国産`。

### 解析与来源边界修正

- `とんぶり` 映射到 `vegetables`；
- `芽胞菌` 与 `クロストリジウム` 映射到 `microbiological`，不再落入未分类；
- 有 MHLW detail 时，必须由 MHLW 本身提供中国来源证据；仅 CAA 写有中国来源而 MHLW 没有时不生成 MHLW-backed record；
- MHLW-backed record 的 product、date 和 reasons 只使用 MHLW 字段，不混入 CAA 摘要；
- CAA 继续只承担发现与交叉核验。

### 首批正式 release

- 新增 `publish-japan-reviewed` 与 `japan_update.py`；
- 要求批准列表与 MHLW reference 完全一致；
- 要求 MHLW authority、官方 MHLW URL/reference 一致、CN 原产、recall action、Schema、unique ID、数量/drop gate 和 0 unclassified hazard；
- 数据与 metadata 成对 staging、原子替换并在失败时恢复旧版本；
- 发布 `data/processed/japan_mhlw_cn.jsonl`：1 record、1 unique ID、0 Schema error、vegetables=1、microbiological=1；
- metadata 包含 PDL 1.0、日英署名、加工与非政府制作/背书声明，以及逐条 provenance；
- CI 新增已提交 Japan release 验证。

### Workflow 加固

- explicit candidate report 新增 China 和 MHLW-backed 最低数量门禁；
- GitHub workflow 现在要求至少 2 条 China records 和 2 条 MHLW-backed records，避免“命令成功但候选为 0”仍显示绿色；
- 新建 Japan 首次候选字段复核文档。

### 验证与状态

- Japan candidate/update 专项测试覆盖 MHLW evidence、分类、批准列表、CAA-only 阻塞、URL/reference mismatch、未分类危害和 PDL metadata；
- 全套 207 项单元测试通过；
- Japan 仍为 `prototype`，等待严格 workflow hosted pass、published-detail audit 与增量/回滚流程。

### 下一步

提交并运行 CI 与 `Smoke test Japan CAA source`。两者通过后，实现已发布 MHLW detail 的字段/status 重查、失败 Issue 和 Japan 增量发布操作手册，再评估升级 `implemented`。

---

## 2026-07-02 · Round 52 · RASFF operations acceptance and Japan explicit review gate

### 触发结果

维护者确认提交 `9294c91` 后 CI 与 `Audit published EU RASFF records` 通过。新版增量/撤回代码、metadata 与 3 条正式 RASFF 记录已在 GitHub 环境验收。RASFF 保持 `prototype`，等待下一次自然新增或官方更正按操作手册完成真实 merge；不为升级状态制造虚假数据变化。

### RASFF 与来源优先级决策

- 本地完整 inventory 因网络代理无法连接官方 RASFF host，失败关闭且没有把 0 条写入 baseline；
- 香港 CFS 技术上接近发布，但官方版权声明仍要求事先书面授权，因此没有授权前不继续构建 production publisher；
- 下一正式化目标改为日本 CAA/MHLW，因为现有 smoke、inventory、candidate 和 MHLW PDL 1.0 依据更完整。

### Japan 显式候选复核

- `candidate-japan-caa` 新增可重复 `--url`；
- 显式 URL 必须是合法 CAA 食品 detail URL，并且仍存在于完整 current inventory；
- 已进入 baseline 的固定样本也可以被选作有界人工复核，不会伪装成新记录；
- workflow 改为固定复核两条中国来源样本与一条非中国对照，从而不再长期只产生空 candidate batch；
- candidate report 新增 `scope` 与 `requested_urls`，区分增量和显式复核。

### 许可边界

- MHLW 利用条款明确：未另行说明的内容按 PDL 1.0 使用，需注明来源；编辑加工时需另行声明加工及主体，且不得表现为政府制作；
- CAA 主站有等价 PDL 1.0 条款，但 `recall.caa.go.jp` 的已检查 about 页只显示版权声明，没有直接展示 PDL 条款；
- 初始发布因此仅允许有已验证 MHLW `RCL...` detail 的记录；CAA 仅用于发现、ID 交叉核验和链接；
- normalized record 改用 MHLW RCL ID、MHLW detail URL 与 MHLW authority；
- 新建 Japan reuse review，并把日文署名、加工声明、非政府制作/背书声明写入统一 attribution 文档；
- 不复制 HTML、图片、logo、附件或第三方内容，CAA-only 表述暂不发布。

### 验证与状态

- Japan candidate/smoke 专项 16 项测试通过；
- 全套 198 项单元测试通过；
- 本地在线显式批次因当前环境到官方站连接不可用而未生成新报告，不能记作 live pass；
- 下一步由 GitHub Runner 运行更新后的 `Smoke test Japan CAA source`，检查 3 个固定 URL 是否生成 2 条 MHLW-backed 中国候选；
- Japan 保持 `prototype`，在 hosted 非空批次与人工字段复核通过前不建立正式发布文件。

### 下一步

提交后手动运行 `Smoke test Japan CAA source`。通过后查看 candidate report 和 JSONL，重点复核混合日本/中国鳗鱼 notice 的产品范围、纯中国来源 `とんぶり瓶詰`、事件日期、MHLW ID 和 recall reason；再实现 MHLW-only 原子发布与 metadata gate。

---

## 2026-07-01 · Round 51 · EU RASFF hosted audit acceptance and release operations

### 触发结果

维护者确认 `Audit published EU RASFF records` 首次 GitHub hosted run 通过。提交 `51b1a1b` 中的 3 条正式记录在 Runner 上逐条重取 detail 后保持一致，发布后状态审计、报告和工作流路径得到首次真实验收。

### 本轮目标

补齐日常维护中最容易出错的三条路径：只合并已批准增量、用同一 reference 替换官方更正、以及有证据地移除官方撤回记录；同时形成可执行的回滚手册。

### 实现内容

- `publish-rasff-reviewed` 新增 `--merge-current`；未在本批次点名的已发布记录保持不变；
- 新增或更正 reference 必须与本批次 `--approved-reference` 完全一致；
- 同 reference 的更正替换旧字段，但保留首次 `retrieved_at`；
- 新增 `--removal-only --remove-reference`，仅允许显式移除已经发布的 reference；
- 未发布 reference 的删除、同一 reference 同时批准和删除、空操作、没有既有 release 时合并均失败关闭；
- 删除仍受最小记录数和 drop percentage 门禁保护；小数据集需要提高阈值时必须人工明确给出；
- release metadata 新增 release mode、完整 release references、本批批准 references 和 removed references；
- 用原 3 条批准记录成功重发内容不变的快照，验证新版 metadata 生成与发布路径。

### 运维手册

新建 `docs/RASFF_OPERATIONS.md`，定义：

- discovery、candidate、人工 detail 复核、增量发布、hosted audit、最后接受 inventory baseline 的顺序；
- active correction、confirmed withdrawal 和 ambiguous `review_required` 的不同处理；
- withdrawn candidate 只作为删除证据，不能直接进入 active JSONL；
- 发布前 pair rollback 与发布后 `git revert` 回滚；禁止 force push 和 `git reset --hard`；
- 发布后人工检查 JSONL、metadata、provenance、署名、数量和无关记录变化的验收表。

### 验证与状态

- 新增 4 项增量运维测试：批准新增、同 reference 更正、显式删除、未知/冲突删除；
- RASFF release 专项 11 项测试通过；
- 全套 195 项单元测试通过；
- RASFF 暂时保持 `prototype`，等待维护者接受操作手册，并完成一次真实增量/更正或撤回演练后再升级 `implemented`。

### 下一步

维护者审核 `RASFF_OPERATIONS.md`。下一次 inventory 出现新/变更 reference 时，严格按手册执行一次 `--merge-current` 发布并通过 hosted audit；若没有自然增量，不为升级状态而伪造数据变化。

---

## 2026-07-01 · Round 50 · EU RASFF first reviewed release and scheduled status audit

### 本轮目标

把已经完成 detail 人工复核的 RASFF 小批量候选升级为可审计的首批正式数据文件，同时保持“发现不等于发布”的人工批准边界。

### 发布门禁与实现

- 新增 `publish-rasff-reviewed` 与 `rasff_update.py`；
- 每条输入必须出现在显式 `--approved-reference` allowlist 中，且批准集合必须与 JSONL 完全一致；
- 重新执行统一 Schema、duplicate ID/reference、来源、CN 原产、origin-based scope、官方 detail URL 和 detail-enriched 字段检查；
- 只有 `record_status: active` 且官方状态为 `ec_validated` 的记录可发布；
- 增加最小/最大记录数与相对上一 release 的数量下降门禁；
- 保留既有记录首次 `retrieved_at`；
- 数据与 metadata 先同时 staging，再成对替换；第二个替换失败时恢复旧数据和旧 metadata；
- metadata 包含 release scope、批准方式/reference、CC BY 4.0 来源与修改声明、非背书声明，以及逐条 source URL、retrieval time、official last update 和 lifecycle provenance。

### 首批真实发布

- 输入为本轮已复核的 3 条 active 增量：`2026.5752`、`2026.5760`、`2026.5781`；
- 发布结果：3 records、3 unique IDs、0 Schema error、event date 2026-06-29 至 2026-06-30；
- 包含 1 条 chemical 与 2 条 other/unclassified 检索标签；后两者属于官方 no-hazard/证书流程记录，不作为未解析危害阻塞；
- 生成 `data/processed/rasff_cn.jsonl` 与 `rasff_cn.metadata.json`；
- 首次受限环境替换临时文件失败，正式目标文件保持不存在；随后在允许文件替换的环境中以同一命令成功，证明失败不会产生半发布。

### 发布后审计 Action

- 新增 `audit-rasff-status.yml`，支持每周与手动运行；
- 对正式 JSONL 中每条记录重取官方 detail；
- `action_required` 或技术失败均返回非零、上传报告并创建/更新维护 Issue；
- 恢复后自动关闭对应 Issue；
- 审计只读，不自动改写或删除已发布记录。

### 验证

- 新增 7 项 release 测试，覆盖 allowlist、active/withdrawn 门禁、首次抓取时间、署名/provenance、双文件回滚和失败不发布；
- 发布 CLI 已用真实 3 条候选成功执行；
- 全套 191 项单元测试通过；
- 新 Action 的首次 GitHub hosted run 尚未执行，因此 RASFF 保持 `prototype`。

### 下一步

提交并手动运行 `Audit published EU RASFF records`。若 hosted audit 通过，人工检查 committed JSONL、metadata 与 artifact；随后写明增量合并、撤回修订和回滚操作手册，再决定是否升级 `implemented`。

---

## 2026-07-01 · Round 49 · EU RASFF expanded detail review and reuse decision

### 触发结果

维护者确认上一轮 RASFF published-record status audit 相关运行通过。项目文档继续按轮次更新；本轮同时清理了来源文档中首次 search-only 评审留下的过时阻塞表述，避免与后续 detail enrichment 结论冲突。

### 本轮目标

在设计首批正式数据发布前，扩大 RASFF detail 人工样本覆盖，并明确欧盟公开数据的署名、修改声明和非背书边界。

### 扩大样本复核

- 显式复核 8 条 reference，并复核默认增量发现的 3 条记录；去重后共 10 条唯一通知；
- 覆盖 alert、information for attention、border rejection 三种 notification classification；
- 覆盖 serious、potentially serious、potential risk、not serious、no risk 五种当前观察到的 risk decision；
- 覆盖 structured hazard 与 no-hazard、corrigendum、active 和 withdrawn；
- 抽查产品包括粉丝、花生、辣椒粉、茶、蟹味鱼糜、果冻糖、花椒、黄原胶和大蒜；
- 所有候选均通过明确中国原产、human-food、ID/reference 一致性、稳定 ID、Schema 和重复检查；
- withdrawn 样本可被正确解析并保留审计证据，但 lifecycle gate 阻止其进入 active 视图。

默认增量发现 `2026.5752`、`2026.5760` 和 `2026.5781` 三条新 reference；逐条 detail 复核后，将 inventory baseline 从 1,211 接受到 1,214。接受 baseline 仅表示发现范围已人工检查，不表示已经发布 RASFF production JSONL。

### 字段与复用决策

- `product.description` 继续作为产品名，search subject 仅作为流程/原因摘要；
- notification classification、risk、basis、官方 status、distribution、last update、hazards、measures 和 follow-up 保留为独立字段；
- 对人类可读 `reasons` 去除重复 hazard 名，但 `official_hazards` 保留官方结构化行，避免损失检测结果或抽样信息；
- 根据欧盟委员会法律声明与 RASFF dataset 元数据，项目仅复用并标准化事实字段，按 CC BY 4.0 提供来源、许可链接、抓取时间、修改声明和非背书声明；
- 不复制欧盟标志、网站视觉资产或没有明确权利状态的第三方附件；
- 新建扩大样本评审与 reuse review，并在统一数据署名文档中加入经批准的中英文展示要求。

### 验证

- 8 条显式 detail batch：8 enriched、0 Schema error、0 duplicate ID；其中 7 active、1 withdrawn，技术门禁通过且生命周期门禁按设计阻塞；
- 默认增量 batch：3 enriched、3 active、0 Schema error，技术与生命周期门禁均通过；
- inventory `--accept-current`：1,214 current、3 new、0 removed、0 changed；
- 新增 duplicate-hazard 展示去重测试；
- 全套 184 项单元测试通过。

### 状态与下一步

RASFF 仍为 `prototype`。下一步实现首批 reviewed production release：生成逐条 attribution/provenance 元数据，执行 fail-closed 质量与数量门禁，原子写入 processed JSONL，并配套失败通知、回滚和 published-record status audit Action。完成真实发布演练与人工验收后，再评估升级为 `implemented`。

---

## 2026-07-01 · Round 48 · EU RASFF published-record status audit framework

### 触发结果

维护者确认加入 lifecycle gate 后的 `Probe EU RASFF source` 运行成功。GitHub Runner 现已验证 active detail 样本保持 active；detail status 漂移会让固定 smoke 失败而不是继续显示绿色。

### 本轮目标

实现未来 RASFF 正式发布后的逐条 detail 重查，弥补 search inventory 不包含最终 notification status 的结构缺陷；同时避免在尚无正式发布数据时伪造 production baseline。

### 审计设计

未来 `data/processed/rasff_cn.jsonl` 本身就是审计 baseline。每条记录必须：

- `source_id` 为 `eu_rasff`；
- source URL 是官方 `screen/notification/{numeric_id}`，无 query/fragment；
- 具有有效 `record_status` 与 `official_last_update`；
- official detail ID/reference 与已发布记录严格一致。

重新标准化当前 detail 后，审计比较 event date、origin、record status、产品、类别、reasons、hazard tags、classification、risk、basis、official status、distribution、last update、structured hazards、measures 和 follow-up types。

### 结果语义

- `passed`：全部已发布字段仍与官方 detail 一致；
- `action_required`：官方 detail 合法但发布快照已过期，例如 active→withdrawn、产品/危害修订或 last-update 变化；CLI 返回非零，未来应触发完整原子重建和维护者通知；
- `failed`：网络、JSON、ID/reference、source URL、origin/scope 或输入验证失败；
- audit 只报告，不原地修改 published JSONL；
- 默认最多 100 条，超过上限失败并要求批准 batching/rate-limit 方案，避免尚无 API 使用说明时直接发出大规模 detail 请求。

### 实现内容

- 新增 `rasff_status_audit.py` 与 `audit-rasff-status`；
- source URL 严格限制官方 HTTPS host 与 numeric notification path；
- 支持逐字段 change sample、previous/current lifecycle、previous/current last update；
- active→withdrawn 和普通产品/危害修订都返回 `action_required`；
- fetch failure、重复 reference、空输入、错误来源和超上限均失败关闭；
- 报告写入 ignored `reports/rasff_status_audit.json`；
- 没有 `data/processed/rasff_cn.jsonl` 前不增加 scheduled audit Action。

### 验证

- 新增 7 项 status-audit 测试，覆盖 unchanged、active→withdrawn、产品/last-update 修订、错误来源/URL、网络失败、空/超限输入和 URL query 拒绝；
- active→withdrawn fixture 返回 `action_required` 并明确列出 `record_status` 与 `official_notification_status`；
- 使用已保存的真实官方 `2026.5192` detail 生成 baseline 后回读：`passed`、1 audited、0 changed；
- 一次在线单条 audit 尝试在本地官方连接长时间无响应，已主动终止且没有生成成功报告；该次不计为 live pass；
- 全套 183 项单元测试通过。

### 下一步

扩大 detail-enriched 人工复核，覆盖主要 classification、risk、hazard/no-hazard 和 lifecycle 组合；同时核对 CC BY 4.0 精确署名与修改声明。完成后设计首个小规模 reviewed production release、原子发布、失败 Issue、回滚和 status-audit Action，再决定是否升级 `implemented`。

---

## 2026-07-01 · Round 47 · EU RASFF lifecycle gate

### 触发结果

维护者确认扩展后的 `Probe EU RASFF source` GitHub Action 运行成功。公开 search probe、13 页 inventory 和新增 notification-detail smoke 均已在 hosted runner 通过；固定样本验证 active China no-hazard、active China hazard 与 India non-China control。

### 本轮目标

把 detail 中的官方 notification status 与 follow-up 转换成明确、可审计的项目生命周期，并防止 withdrawn 或语义矛盾记录因为“Schema 通过”而进入 active 发布视图。

### 生命周期决策

- `ec_validated` 且没有 withdrawal follow-up：`record_status: active`；
- `ec_withdrawn`：`record_status: withdrawn`，保留记录用于审计，不静默删除；
- 未知官方状态：`record_status: review_required`；
- `ec_validated` 同时出现 withdrawal follow-up：矛盾状态，映射 `review_required`；
- `corrigendum` 本身不撤回仍为 `ec_validated` 的记录。

消费者当前有效视图未来默认只包含 `active`；withdrawn 和 review-required 仍应能在审计/历史视图查询。该决策不等于已经完成生产发布。

### 实现内容

- 统一 schema 新增可选 `record_status`，枚举 active、withdrawn、review_required；
- detail normalization 根据官方 status 和 follow-up 类型确定生命周期；
- 保留 `official_followup_types`，使 corrigendum 与 withdrawal 证据可追溯；
- candidate evidence sample 增加 project record status；
- candidate report 新增 active/withdrawn/review-required 计数、独立 `lifecycle_gate_status` 和 blockers；
- 技术 parse/Schema `status` 与生命周期 gate 分离：withdrawn 可被正确解析并保留，但不能通过 active gate；
- fixed detail smoke 现在要求两条 China 样本保持 active；若官方后续撤回其中一条，workflow 会明确失败而非继续显示绿色。

### 真实验证

- `2026.5752`：官方 `ec_validated`，包含 `corrigendum`，项目状态 `active`；默认增量候选 lifecycle gate `passed`；
- `2026.5575`：官方 `ec_withdrawn`，包含 request for withdrawal 与 withdrawal of original notification，项目状态 `withdrawn`；
- 真实增量候选仍为 1 条 `Vermicelli`，detail enriched、Schema 通过、active=1、withdrawn=0、review_required=0；
- withdrawn fixture 技术解析通过但 lifecycle gate `blocked`，证明两种门禁不会混淆。

### 验证与状态

- 新增 lifecycle 状态机测试，覆盖 active+corrigendum、withdrawn、矛盾 withdrawal follow-up 和未知状态；
- 新增 withdrawn candidate lifecycle-gate 测试；
- RASFF detail/detail-smoke/candidate 共 21 项专项测试通过；
- 全套 176 项单元测试通过；
- RASFF 保持 `prototype`。

### 剩余阻塞与下一步

search inventory 不提供最终 notification status，因此它无法发现一个既有 reference 仅在 detail 中变为 withdrawn。下一步实现“已发布 reference detail-status audit”：为未来 RASFF processed release 保存最小 ID/reference/status/last-update baseline，周期性重查每条已发布记录，报告 active→withdrawn、active→review_required 和 last-update 变化。在还没有 RASFF 正式发布记录时，不伪造 production status baseline。

---

## 2026-07-01 · Round 46 · EU RASFF official detail enrichment

### 本轮目标

解决首次候选复核发现的核心字段缺口：公共 search `subject` 不是可靠产品名，并且 search 不暴露 hazard detail 与最终 notification status。

### 官方 detail endpoint

使用无头浏览器打开 RASFF Window 官方 notification 页面并记录页面自身网络请求，确认公开 endpoint：

`GET /rasff-window/backend/public/notification/view/id/{notification_id}/en/`

该 endpoint 无需登录，与 search 使用同一 `webgate.ec.europa.eu/rasff-window/backend/public/` 边界。真实 JSON 提供：

- 独立 `product.description` 与 product category/type；
- hazard name、hazard category、检测值、单位、抽样日期和最大允许值；
- notification basis、classification、risk decision 和 status；
- distribution status、measures 和 last update；
- 通过 organization flag 明确区分 ORIGIN、NOTIFYING、DISTRIBUTION 和 OPERATOR；
- follow-up/corrigendum/withdrawal 信息。

### 真实字段验证

- `2026.5752` / ID `854651`：search subject 只有“可能需要兽医检查”，detail 产品名为 `Vermicelli`，status `ec_validated`，无 hazard，basis 为 released border control；
- `2026.5192` / ID `850740`：产品 `Groundnut kernels`，hazard `Aflatoxin B1 - mycotoxins`，status `ec_validated`；
- `2026.5711` / ID `827209`：产品 `Rice`，ORIGIN 为 `IN`，作为非中国对照不生成中国候选；
- `2026.5575` / ID `852931`：产品 `Pepper Powder`，hazard `anthraquinone - pesticide residues`，检测 `0,078 mg/kg`、限值 `0,02 mg/kg`，但 detail status 已是 `ec_withdrawn`，follow-up 包含 withdrawal of original notification。

最后一条揭示了新的生产风险：search inventory 没有暴露 withdrawn status，因此仅比较 search fingerprint 不能保证捕获既有通知的撤回。

### 实现内容

- 新增 `rasff_detail.py`，限制使用官方 public detail URL；
- 校验 detail ID/reference、日期、产品、类别、类型、risk、status、origin flags、hazards、measures 与 distribution；
- detail ORIGIN 必须显式包含 `CN` 且 product type 必须是 `food` 才能标准化；
- `product.description` 替代 search subject 成为正式候选 `product_name`；
- 有 hazard 时以官方 hazard name 作为 reasons，并用确定性规则生成检索标签；无 hazard 时保留 subject 作为监管原因摘要；
- 扩展统一 schema，新增 official classification、risk、basis、status、distribution、last update、结构化 hazards 与 measures；
- `candidate-rasff` 现在逐条抓取并校验 detail，search 与 detail ID/reference 不一致即失败关闭；
- 候选报告增加 detail enriched count 和 withdrawn count；
- 新增 `smoke-rasff-detail`，固定两条 active China 样本和一条 India control；
- 扩展 RASFF Action，在 probe 与 inventory 后运行 detail smoke 并上传诊断报告；
- 更新首次候选复核状态为 `detail_enriched_pipeline_passed_production_blocked`。

### 真实运行结果

- 最终固定 detail smoke：2 China details、1 India control、1 hazard、0 control emission、0 withdrawn active sample、0 Schema 错误、0 duplicate ID；
- detail-enriched 默认增量仍只选中 `2026.5752`；
- 候选产品名由错误的流程 subject 修正为 `Vermicelli`；
- 候选保留官方 classification、risk、basis、status、distribution、measures 与 detail last update；
- 本地 candidate JSONL 和报告继续被 Git 忽略，不上传 artifact。

### 验证与状态

- 新增 7 项 detail parser/normalizer 测试，包括 official mycotoxin category 到 chemical 检索标签的映射；
- 新增 4 项 detail smoke 测试；
- detail、detail smoke 与 candidate 共 19 项专项测试通过；
- 全套 174 项单元测试通过；
- 真实 detail smoke 与真实 detail-enriched candidate 均通过；
- RASFF 继续保持 `prototype`，等待 hosted detail smoke 验收；
- 即使 hosted smoke 通过，withdrawal/corrigendum 与已发布记录 status 重查策略仍是正式发布阻塞项。

### 下一步

提交并手动运行扩展后的 `Probe EU RASFF source`。通过后设计 withdrawal/corrigendum 状态机：明确 active、withdrawn、corrigendum 的数据表示，决定撤回记录是保留带状态、生成 tombstone 还是从当前视图排除，并确保已发布 reference 会周期性重查 detail status。随后扩大 detail-enriched 人工复核，最后完成 CC BY 4.0 署名和生产发布门禁。

---

## 2026-07-01 · Round 45 · EU RASFF incremental candidates and field review

### 触发结果

维护者确认加入完整 13 页 inventory 后的 `Probe EU RASFF source` GitHub Action 运行通过。RASFF 的 probe 与完整 pagination/baseline 现均已在 hosted runner 验收，`prototype` 状态成立。

### 本轮目标

实现只处理新增/修订 reference 的本地候选管线，并用真实样本判断 RASFF 公共搜索字段是否已经足以进入正式发布。

### 实现内容

- 新增 `rasff_candidates.py` 与 `candidate-rasff`；
- 默认完整扫描后仅选择 baseline 中不存在或字段指纹变化的 reference；
- repeated `--reference` 支持维护者明确选择小规模当前记录做人工复核；
- 明确 reference 必须符合 RASFF 格式且存在于当前 China+food 完整 inventory，否则失败关闭；
- `--max-candidates` 在意外大批量时不输出部分 JSONL，要求维护者显式提高上限；
- 每批候选统一使用同一 retrieved timestamp，执行 Schema、重复 ID、日期、类别和风险标签质量检查；
- 诊断报告单独保留官方 notification ID、reference、原始日期、subject、通知国、产品类别/类型、classification、risk 和 origins；
- candidate JSONL 与报告均由 Git 忽略，不加入 scheduled Action，不上传 artifact。

### 真实候选结果

显式复核批次包含 `2026.5655`、`2026.5625`、`2026.5575`、`2026.5514`、`2026.5506`：

- 5 条均为官方 product type `food`；
- 5 条均有 explicit `CN` origin；
- 5 条候选 Schema 错误 0、重复 ID 0；
- 日期范围 2026-06-22 至 2026-06-26；
- baseline 建立后官方总数从 1,211 增至 1,212，默认增量模式准确选中唯一新增 reference `2026.5752`；
- 新增候选 Schema 错误 0，未重新生成其余 1,211 条 baseline 记录。

### 人工复核发现

- 公共 search payload 只有 `subject`，不是独立产品名；
- 多数 subject 混合产品、违规原因和流程描述；
- 新增 `2026.5752` 的 subject 为 `Consignment possibly subject to veterinary checks`，完全没有可识别产品，证明当前 `product_name=subject` 不能用于正式发布；
- `2026.5575` 的 subject 是 pepper powder，但官方 search category 是 nuts/seeds；项目必须保留并标注官方类别，不能根据文字擅自纠正；
- official notification classification 与 risk decision 目前只在诊断证据中，正式 schema 需要专用字段或来源 metadata；
- 通用 hazard 规则使多数样本落入 `other_or_unclassified`，需要 detail-level hazard evidence。

### 验证与状态

- 新增 8 项 candidate 测试，覆盖 new/changed/removed 选择、显式复核、非法/缺失 reference、Schema/evidence、候选上限、空增量、网络失败和完整 pipeline；
- RASFF candidate 专项测试 8 项通过；
- 全套 163 项单元测试通过；
- 真实显式批次和真实默认增量批次均通过技术门禁；
- 新增 `docs/reviews/RASFF_INITIAL_CANDIDATE_REVIEW.md`，状态为 `pipeline_passed_publication_blocked`；
- RASFF 保持 `prototype`，不得把当前 subject 映射作为正式产品名发布。

### 下一步

定位并验证 RASFF Window 使用的官方 public notification-detail JSON 请求，确认是否提供独立产品名、hazard category/detail、action、distribution 与更多日期。取得 detail evidence 后扩展 schema 中的 official classification/risk 字段，并用至少两条中国记录和一条非中国对照重新复核；最后再处理 CC BY 4.0 署名和生产门禁。

---

## 2026-06-30 · Round 44 · EU RASFF prototype acceptance and full inventory

### 触发结果

维护者确认 `Probe EU RASFF source` GitHub Action 首次运行通过。官方公开配置、目录、China+food 双过滤、印度对照、Schema 标准化和失败关闭逻辑已在 hosted runner 完成验收，RASFF 达到只读 `prototype` 门槛。

### 本轮目标

把单页健康 probe 扩展为完整、可重复的增量 inventory，并在不提交完整监管文本的前提下识别新增、撤下和字段修订。

### 实现内容

- `build_search_payload` 支持显式页码，新增保留 `totalPages` 的页面解析接口；
- 新增 `inventory-rasff` 与 `rasff_inventory.py`；
- 每次从官方目录动态解析 China 与 human-food ID；
- 以 100 条/页完整扫描，逐页要求 `totalElements` 和 `totalPages` 一致；
- 校验报告页数与总数、每页预期条数、最终总数、China+food scope、notification ID 和 reference 唯一性；
- 扫描期间总数/页数变化、重复、缺页、越界类型或网络错误均失败关闭并生成诊断报告；
- baseline 仅保存官方 notification ID、reference 和选定公开字段 SHA-256，不保存 subject 或完整 API 记录；
- 指纹覆盖日期、subject、通知国、产品类别/类型、classification、risk、published 和 origins，可区分 new、removed 与 changed；
- `--accept-current` 仅接受完整成功扫描，失败或 `--max-pages` 部分扫描禁止替换 baseline；
- 扩展 RASFF Action，在 probe 后运行完整 inventory，并上传两份诊断报告；
- 将来源登记与 checklist 从 `candidate` 升级为 `prototype`。

### 真实 inventory 结果

- China-origin human-food：1,211；
- 每页上限：100；
- 官方报告页数：13；
- 完整扫描页数：13；
- 扫描记录数：1,211；
- 重复 notification ID：0；
- 重复 reference：0；
- 越界来源/产品类型：0；
- baseline 文件约 197 KiB，只含最小 ID/reference/fingerprint 状态；
- 建立 baseline 后立即完整回读：`unchanged`，0 new、0 removed、0 changed。
- reference 年份覆盖 2018–2026，其中 2018 年 4 条、2019 年 12 条；鉴于公开说明通常描述 2020 年起可检索，项目只记录实际 API 返回，不宣称 2020 年前完整覆盖。

以上数量是 2026-06-30 的官方 API 快照诊断，会随新通知和修订变化。

### 验证与状态

- 新增 8 项 inventory 测试，覆盖多页收集、扫描中总数变化、重复 reference、scope 漂移、new/removed/changed、最小状态回读、网络失败报告和指纹变化；
- RASFF probe 与 inventory 共 18 项专项测试通过；
- 全套 155 项单元测试通过；
- 首次完整真实扫描及 baseline 回读通过；
- RASFF 现为 `prototype`，仍不生成 candidate artifact 或写入 `data/processed/`。

### 下一步

提交并再次手动运行扩展后的 `Probe EU RASFF source`，验证 GitHub Runner 能稳定完成 13 页 inventory。通过后实现 `candidate-rasff`：只处理 baseline 之后的新增/修订 reference，先生成 ignored JSONL 与人工复核报告，再决定 notification subject 是否可作为正式产品名，并完成 CC BY 4.0 署名文案。

---

## 2026-06-30 · Round 43 · EU RASFF official public API probe

### 触发结果

维护者确认 `feat: add grouped SAMR local candidates` 对应验证通过。SAMR 分组候选实现至此完成本轮验收，但按既定发布门禁继续保持 `candidate`，不把本地候选误当正式数据。

### 本轮目标

回到欧盟 RASFF，解决此前“API endpoint、认证模式和真实字段未知”的阻塞，建立一个最小、只读、可重复且失败关闭的官方来源探针。

### 官方接口与范围验证

- 确认 RASFF Window 的官方公开页面调用 `backend/public/notification/search/consolidated/en/` JSON POST endpoint；
- 公开配置的 `openPortalLink` 指向 data.europa 的 `restored_rasff` 数据集；
- 从官方 country catalog 动态读取 China `5075` / `CN` 与 India `5118` / `IN`，不在生产逻辑中把数字 ID 当成永久常量；
- 从官方 product-type catalog 动态读取 human food `283`；
- 使用 `originCountry=[China]` 与 `notificationType=[food]` 双过滤，排除 feed、food contact material、animals 和 other；
- 使用 India+food 作为非中国对照，避免仅凭主题文字或通知国家误判来源；
- API 用户指南下载仍为 404，但官方公开端点、请求体、目录和字段均已由真实响应确认，因此不再阻塞最小健康探针。

### 实现内容

- 新增 `rasff_probe.py` 与 `probe-rasff` CLI；
- 限制网络请求为 `webgate.ec.europa.eu` 的 HTTPS public API 路径；
- 使用 curl IPv4、HTTP/1.1、重试、连接/总超时和 JSON stdin POST；
- 验证 `notifId`、reference、validation date、subject、product category/type、classification、risk decision 和 explicit origin countries；
- 只将 product type 为 `food` 且 `originCountries` 含 `CN` 的结果标准化；
- 新增 `rasff_notification` action type，避免把 alert、border rejection 和 information notification 错归为单一 recall；
- 公共搜索没有独立产品名字段，当前保留官方 notification subject 作为 `product_name` 与 reason，不做脆弱的文本裁剪；
- 新增每周及手动 `Probe EU RASFF source` Action，只上传 30 天诊断 artifact，不提交候选或正式数据；
- 更新 README、来源登记、来源评估、发布前 checklist 和忽略规则。

### 真实探针结果

2026-06-30 本地 live probe：

- 中国来源人类食品总数：1,211；
- 返回并标准化样本：10；
- 印度来源人类食品总数：2,083；
- 非中国对照样本：2，错误生成中国记录：0；
- Schema 错误：0；
- 重复稳定 ID：0；
- 样本日期范围：2026-06-19 至 2026-06-26；
- 10 条样本覆盖 7 个官方产品类别。

以上数量是当日 API 诊断结果，会随监管数据更新而变化，不作为固定数据承诺。

### 验证与状态

- 新增 10 项 RASFF 回归测试，覆盖官方 URL、JSON POST、动态目录、双过滤、关键字段、非中国排除、Schema、网络失败、filter drift 和日期标准化漂移失败关闭；
- 全套 147 项单元测试通过；
- 本地真实 `probe-rasff` 通过；
- RASFF 继续保持 `candidate`，等待新 workflow 提交后首次 GitHub Runner 验收；
- 不发布历史快照，不写入 `data/processed/`。

### 下一步

提交本轮改动并手动运行 `Probe EU RASFF source`。若 hosted Action 通过，可把 RASFF 升为只读 `prototype`；随后设计稳定分页/增量 inventory、候选批次和人工复核，再处理 CC BY 4.0 署名、subject/product 字段决策及生产发布门禁。

---

## 2026-06-30 · Round 42 · China SAMR grouped local candidates

### 触发结果

维护者确认加入完整 inventory 后的 `Probe China SAMR sampling source` GitHub Action 运行通过。SAMR 的只读公告健康检查与 78 条 URL baseline 监控均已在 GitHub Runner 验收。

### 本轮目标

实现产品级候选解析，但继续遵守复用边界：候选 JSONL 仅在本地生成，不加入定时 workflow，不作为公开 artifact 上传。

### 工作簿复核与解析

- 按 spreadsheet skill 使用官方工作簿复核行结构、日期值和合并区域；
- 直链酒类 XLSX 的 5 个物理数据行聚合为 3 个抽样事件；
- ZIP 中 21 个工作簿的 73 个物理数据行聚合为 46 个抽样事件，其中 27 行为延续行；
- 聚合同时识别序号变化和抽样编号变化；同一序号在不同合并区域重复出现时仍保留为同一事件；
- 一个抽样事件保留全部不合格项目、检验值、标准值、标签要求和两个备注列；
- 支持 Excel 数字日期、普通文本日期及 `购进日期：2025/4/12` 等前缀形式；
- `抽样编号` 作为来源记录 ID，46 条候选无重复来源 ID 或项目 ID；
- 新增本地手动 `candidate-china-samr` 命令，支持官方详情页配合本地 XLSX/ZIP；
- 新增 6 项聚合、日期、ZIP、scope、失败关闭和 Schema 回归测试。

### 重要范围修正

首次映射曾尝试依据 `标称生产企业地址` 判断中国来源，真实候选立即暴露出错误：进口食品可能在该字段包含中国进口商、经销商或代理地址。该字段不能证明产品原产地。

SAMR 候选现统一使用：

- `regulatory_scope: domestic_market`；
- `market_country: CN`；
- `origin_country: unknown`。

生产企业地址继续作为官方证据字段保留，包含大陆地区词的数量仅作为诊断，不再转成原产地。46 条 ZIP 候选中 37 条有大陆生产企业地址证据，但全部 46 条均诚实保留为来源国未知。

### 候选质量结果

- ZIP 工作簿：21；
- 物理数据行：73；
- 聚合事件：46；
- 延续行：27；
- 重复抽样编号：0；
- Schema 错误：0；
- 来源国：46 `unknown`；
- 类别覆盖：14 类；
- 风险标签覆盖：chemical、microbiological、labeling、adulteration、composition/quality；
- 新增 `docs/reviews/CHINA_SAMR_INITIAL_CANDIDATE_REVIEW.md`，状态为 `conditionally_passed`。

### 验证

- 全套 137 项单元测试通过；
- 真实直链 XLSX 候选命令通过：5 行聚合为 3 条；
- 真实 ZIP 候选命令通过：73 行聚合为 46 条；
- 两批候选均无 Schema 或重复 ID 错误；
- `git diff --check` 通过，仅有 Windows LF/CRLF 提示。

### 状态与下一步

SAMR 继续保持 `candidate`，不会因为解析成功就升级。下一步需要扩大人工字段抽样，定义修订公告中同一抽样编号的更新语义，验证历史年份的类别/风险覆盖，并解决标准化事实与简短原因文本的复用依据。完成后再评估升级 `prototype`；随后回到欧盟 RASFF。

---

## 2026-06-30 · Round 41 · China SAMR complete notice inventory

### 触发结果

维护者确认首次 `Probe China SAMR sampling source` GitHub Action 运行通过。SAMR 官方公告发现、通报详情、ZIP/XLSX 下载和核心字段检查已在 GitHub Runner 上完成首次验收；来源仍保持 `candidate`。

### 本轮实现

- 扩大公告标题规则，同时接受“食品抽检不合格情况的通报”和“通告”；
- 验证官方 CMS 的 `paramJson.pageNo/pageSize` 分页参数；
- 确认服务器单页最多返回 99 条，完整 259 条列表需要 3 页；
- 新增 `inventory-china-samr`，完整扫描时要求各页总数一致、每页非空且物理列表项合计严格等于官方总数；
- 支持 `--max-pages` 诊断，但部分扫描禁止通过 `--accept-current` 替换 baseline；
- 建立 `data/state/china_samr_notice_urls.json` 首个 URL baseline；
- 扩展 SAMR GitHub Action，在 probe 后运行完整 inventory 并上传两份结构诊断报告；
- 更新 README、来源登记、来源评估、checklist 和忽略规则；
- 新增 7 项 inventory 回归测试。

### 真实 inventory 结果

- 官方 CMS 报告 259 条全部类型列表项；
- 3 页实际返回 99、99、61 条，合计严格为 259；
- 其中 78 条标题符合批次食品抽检不合格通报/通告；
- baseline 覆盖 2021 至 2026 年公告 URL；
- 78 个 URL 无重复；
- 使用同一完整官方快照回读 baseline，inventory 状态为 `unchanged`：78 current、0 new、0 removed。

### 验证

- 全套 131 项单元测试通过；
- baseline 为 78 个唯一、排序后的官方 HTTPS URL，声明数量与数组长度一致；
- `inventory-china-samr --help`、来源 registry JSON 和 baseline JSON 解析通过；
- `git diff --check` 通过，仅有 Windows LF/CRLF 提示。

### 状态与下一步

首次 probe Action 已通过；加入 inventory 后的扩展 workflow 仍需提交并再次手动运行。通过后进入产品行标准化：先解析一份直链 XLSX 通报与一份 ZIP 通报，完成 `抽样编号` 聚合、延续行前向填充、Excel 日期转换和修订语义，再决定是否生成仅供本地人工复核的 candidate。

---

## 2026-06-29 · Round 40 · China SAMR national sampling source probe

### 本轮目标

在台湾 TFDA 正式发布完成后，启动中国大陆国家级食品安全监督抽检 source spike；验证官方公告能否自动发现、附件是否有稳定产品字段，并明确境内抽检与境外中国来源事件的统计边界。

台湾生产 workflow 本轮再次运行后远端仍停在 `21e8d22`。由于官方快照没有变化，工作流没有生成空数据提交，行为符合预期；台湾 `implemented` 状态不变。

### 来源发现与边界

- 定位国家市场监督管理总局食品安全抽检监测司公告列表、产品结果查询系统和两种官方附件格式；
- 官方公告 CMS 响应报告 259 条列表项，当前测试页发现 4 条“批次食品抽检不合格情况”通报；
- 产品结果查询系统要求 image token 与滑块结果，不作为无人值守采集入口，也不尝试绕过；
- 自动化改用官方公告列表、公告详情与 XLSX/ZIP 附件；
- 来源范围登记为 `domestic_regulatory_scope`，未来不得与境外进口拒绝、召回或边境不合格事件静默混合统计；
- SAMR 网站声明没有提供清晰开放数据许可证，当前只发布结构诊断，不提交官方附件、候选 JSONL 或正式数据。

### 实现内容

- 新增 `probe-china-samr` 命令和 `china_samr_probe.py`；
- 限制请求为 SAMR 官方 HTTPS host；
- 解析官方 CMS JSON 中的列表总数、公告标题、日期和 URL；
- 解析通报发布日期、声明的不合格批次数和 XLSX/ZIP 附件；
- 使用 Python 标准库读取 XLSX XML，不增加运行时 spreadsheet 依赖；
- 同时支持直链 XLSX 与 ZIP 内多个 XLSX，并检查八个核心字段；
- 新增只读 `Probe China SAMR sampling source` GitHub Action，仅上传诊断报告；
- 新增来源评估文档、来源登记、README badge/说明、发布前 checklist 状态和忽略规则；
- 新增 7 项 SAMR 回归测试。

### 真实样本结果

- 一份 46 批次通报 ZIP 包含 21 个分类工作簿；
- 21 个工作簿全部通过核心字段检查，列数范围为 16–19；
- 73 个物理数据行对应 46 个唯一 `抽样编号`；
- 结果确认同一食品的多个不合格项目会占用延续行，正式解析必须按抽样编号聚合或前向填充，不能把每行当作独立事件；
- 本地用刚下载的官方列表、公告和 ZIP 快照完成离线端到端 probe：`passed`、259 条列表项、4 条当前批次通报、21 个工作簿、73 行、46 个唯一抽样编号。

### 验证与状态

- 全套 124 项单元测试通过；
- `data/sources.json` 解析通过，`sources` 命令显示 `cn_samr_sampling` 为 `candidate`；
- CLI help、官方列表解析、公告解析、ZIP/XLSX 字段检查通过；
- `git diff --check` 通过，仅有 Windows LF/CRLF 提示；
- SAMR 保持 `candidate`，新 Action 尚待提交后首次 GitHub 手动运行验收。

### 下一步

提交并手动运行 `Probe China SAMR sampling source`。通过后实现公告完整分页与 URL baseline，再实现按抽样编号聚合、延续行、Excel 日期及修订语义；完成境内 scope 模型和复用依据评审后，才评估升级 `prototype`。中国 source spike 达到该阶段后回到欧盟 RASFF。

---

## 2026-06-29 · Round 39 · Taiwan TFDA implemented acceptance

### 验收证据

- 正确的 `Update Taiwan TFDA data` workflow 从 `main` 运行通过；
- GitHub Actions 自动生成并推送提交 `21e8d22 data: update Taiwan TFDA noncompliance records`；
- 正式提交包含 `data/processed/taiwan_tfda_cn.jsonl`、同名 metadata 和 `reports/taiwan_tfda_quality.json`；
- JSONL、metadata 和质量报告记录数一致，均为 388；
- 质量报告状态为 `passed`，Schema 错误 0、重复 ID 0、解析错误 0、未分类风险 0；
- 正式数据日期范围为 2023-01-03 至 2026-06-23；
- metadata 包含提供机关、数据集名、抓取时间、官方链接、授权链接和署名文本。

### 状态变更

- 台湾 TFDA 从 `prototype` 正式升级为 `implemented`；
- 更新来源登记、README、发布前 checklist、来源文档与首次候选复核记录；
- 台湾成为 FDA 之后第二个正式生产数据源。

### 下一步

开始中国大陆国家级食品安全抽检 source spike。中国境内抽检必须使用独立范围标签，不与境外监管机构发现的中国来源食品混合统计；先验证国家级来源的结构化访问、公告覆盖、字段证据、增量标识和再利用条件，再决定是否进入 prototype。

---

## 2026-06-29 · Round 38 · Taiwan first-publish evidence hardening

### 触发原因

维护者报告台湾生产 workflow 运行绿色，但同步并刷新全部远端引用后，`origin/main` 仍停在生产代码提交 `38b5246`。仓库中没有 `data/processed/taiwan_tfda_cn.jsonl`、metadata、质量报告或自动数据提交，因此不能仅凭绿色状态把台湾标为 `implemented`。

### 本轮修正

- 生产 workflow 强制只能从 `main` 发布，其他分支直接失败；
- 更新命令后检查 JSONL、metadata 与质量报告均存在且非空；
- 比较 JSONL 行数、metadata `record_count` 和质量报告 `record_count`，三者必须一致；
- 首次发布通过 `git cat-file` 判断正式 JSONL 尚未进入 HEAD；
- 首次发布若没有 staged data files，workflow 明确失败，不允许绿色 no-op；
- commit 前输出 `git status --short`，便于诊断；
- 推送改为显式 `git push origin HEAD:main`，避免 checkout 处于 detached HEAD 或错误分支时没有发布到主分支；
- 来源继续保持 `prototype`，直到远端出现可核验的自动数据提交。

### 下一步

提交修正后重新运行 `Update Taiwan TFDA data`，确认日志出现 `Verified ... mutually consistent Taiwan TFDA records`，并确认远端新增 `data: update Taiwan TFDA noncompliance records` 提交。完成后再升级为 `implemented`，随后开始中国大陆国家级抽检 source spike。

---

## 2026-06-29 · Round 37 · Taiwan TFDA production publishing gate

### 本轮目标

将已通过候选复核的台湾 TFDA 来源推进到首次正式发布前的最后阶段：完整快照重建、生产质量门禁、数据署名、原子替换、失败通知和独立自动发布 workflow。

维护者已确认上一轮修正后的 388 条全量候选 GitHub Action 运行通过，首次候选复核状态由 `conditionally_passed` 更新为 `passed`。

### 授权与署名核验

- 官方数据集页面确认提供机关为“卫生福利部食品药物管理署”、数据集名为“不符合食品资讯资料集”；
- 授权方式为“政府资料开放授权条款-第1版”，允许不限目的利用、改作及再授权，但要求明确显名；
- 新增 `docs/DATA_ATTRIBUTION.md`；
- 每次发布同时生成 metadata，记录提供机关、数据集名、抓取时间、记录数、官方链接、授权链接与署名文本；
- 项目 MIT License 只覆盖代码，不将监管来源数据重新声明为 MIT。

### 生产更新器

- 新增 `update-taiwan-tfda`，每次从官方完整快照重建正式数据，不增量拼接；
- 正式路径为 `data/processed/taiwan_tfda_cn.jsonl`、同名 metadata 和 `reports/taiwan_tfda_quality.json`；
- 门禁要求：官方源不少于 2,000 条、正式记录不少于 300 条、相对上次下降不超过 25%、Schema/重复 ID/解析错误均为 0、未分类风险为 0；
- 对 ID 未变化的记录保留首次 `retrieved_at`；官方修订导致完整行哈希改变时按新记录处理；
- 质量失败时只写诊断报告，不替换正式数据或 metadata；
- 通过门禁后使用同目录临时文件与 `Path.replace` 原子替换。

### 自动化与恢复

- 新增独立 `Update Taiwan TFDA data` Action，不与只读 probe 混合；
- workflow 每周或手动运行测试和生产更新，仅提交通过验证的数据、metadata 与质量报告；
- 失败时创建或更新唯一 Issue，恢复后自动评论并关闭；
- 回滚方式为 revert 自动数据提交，失败质量报告保留在 workflow artifact。

### 验证结果

- 全套 117 项单元测试通过；
- 真实官方快照的内存生产构建通过：388 条记录、Schema 错误 0、重复 ID 0、未分类风险 0；
- 覆盖最小源数量、最小发布数量、数量突降、未分类风险、失败不发布、原子发布异常诊断、首次抓取时间保留、署名 metadata 和临时文件替换顺序；
- `data/sources.json` 通过 JSON 解析；
- `git diff --check` 通过（仅有 Windows LF/CRLF 提示）。

### 验收边界与下一步

受管桌面沙箱允许写临时文件但拒绝 Windows 文件替换操作，因此本地未生成正式发布文件；原子替换流程由独立单元测试覆盖。首次真正的端到端发布验收由 GitHub Linux Runner 完成。Action 通过并产生经复核的自动数据提交后，再把台湾从 `prototype` 改为 `implemented`。

产品顺序建议：台湾正式落地后，先对中国大陆官方抽检来源做独立 source spike，再进入欧盟 RASFF；境内抽检与境外发现中国来源食品必须使用不同的数据范围标签和统计口径。

---

## 2026-06-28 · Round 36 · Taiwan TFDA first candidate acceptance review

### 本轮结果

维护者确认带 inventory 与 candidate 的台湾 GitHub Action 已运行通过。随后对首次全量候选执行字段回链、食品范围、类别和风险标签复核；验收发现并修正了三类规则问题，候选数由 384 调整为 388。

### 全量回链检查

- 2,472 条官方记录与候选使用完整记录哈希一一关联；
- 每条候选均来自官方 `產地` 明确为中国大陆/中国的记录；
- 产品名、发布日期、出口商、税则号、原因和详细检出说明均与原始行一致；
- 修正后 388 条候选覆盖集合与确定性食品范围完全一致；
- 388 个 candidate ID 与 source record ID 均无重复。

### 复核发现与修正

- 辣椒红、碳酸氢钠、活化酸性白土、辣椒树脂属于食品添加物或加工助剂，但税则位于第 24 章之外；新增四个窄范围税则前缀白名单；
- 5 条税则 `1905.90.10` 空胶囊不应标为烘焙谷物，改为 `food_capsules`；
- 10 条“其他卫生项目”详情实际为戴奥辛、多氯联苯、环氧乙烷、磷酸盐、氯化物或污染，补充化学风险词表；
- 修正后 388 条候选中 `other_or_unclassified` 降为 0；
- 其余 188 条被排除的中国来源记录均为餐盒、纸托、刀具、吸管、蒸笼布等食品接触器具或非食品相关产品。

### 文档与验证

- 新增 `docs/reviews/TAIWAN_TFDA_INITIAL_CANDIDATE_REVIEW.md`；
- 更新台湾来源文档、README、来源登记和发布前 checklist；
- 全套 109 项单元测试通过；
- 真实官方快照 probe 通过：2,472 条总记录、576 条中国来源、388 条中国食品/添加物候选；
- 全量 candidate 通过：Schema 错误 0、重复 ID 0、未分类风险 0；
- `git diff --check` 通过（仅有 Windows LF/CRLF 提示）。

### 状态与下一步

本地首次候选复核为 `conditionally_passed`，台湾仍保持 `prototype`。提交修正后需要再次手动运行 Action 并勾选 `include_current`，确认 artifact 中为 388 条候选；之后处理授权署名和 production 发布门禁。

---

## 2026-06-28 · Round 35 · Taiwan TFDA incremental inventory and candidates

### 本轮结果

维护者确认上一轮 `Probe Taiwan TFDA source` GitHub Action 已通过。台湾源继续从只读 probe 推进到增量 inventory 与候选 JSONL 阶段，但仍保持 `prototype`，不会写入 `data/processed/`。

### 本轮改动

- 新增 `inventory-taiwan-tfda`，用完整规范化官方记录的 SHA-256 与基线比较；
- 建立 `data/state/taiwan_tfda_record_ids.json` 首个基线，包含 2026-06-28 快照的 2,472 条记录；
- 新增 `candidate-taiwan-tfda`，正常模式只处理基线后新增记录；
- 增加显式 `--include-current` 人工复核模式，可生成当前完整候选批次；
- 中国来源只接受官方 `產地` 字段，食品范围继续使用确定性税则规则；
- 新增台湾税则食品分类、中文风险标签、统一 Schema 映射和失败关闭诊断；
- 扩展台湾 GitHub Action：只下载一次一致快照，依次运行 probe、inventory、candidate，并上传报告与候选 artifact；
- 更新来源文档、README、来源登记、发布前 checklist 和忽略规则。

### 身份与修订语义

TFDA 数据没有原生行 ID。基线使用完整 canonical JSON 的 SHA-256；因此官方修改一条既有记录时，inventory 会报告一个旧哈希被移除、一个新哈希出现。项目不把二者自动合并，留给维护者按 artifact 复核。

### 验证结果

- 全套 108 项单元测试通过；
- 真实全量复核模式读取 2,472 条记录，生成 384 条中国来源食品候选；
- 384 条候选 Schema 错误 0、重复 ID 0，日期范围 2023-01-03 至 2026-06-23；
- 首个基线建立后，正常 inventory 为 `unchanged`：0 新增、0 移除；
- 正常 candidate 增量为空并通过：0 条 scoped record、0 条候选；
- `data/state/taiwan_tfda_record_ids.json` 含 2,472 个唯一 64 位哈希；
- `git diff --check` 通过（仅有 Windows LF/CRLF 提示）。

### 下一步

提交后重新手动运行扩展后的 `Probe Taiwan TFDA source`。首次运行建议勾选 `include_current`，下载 384 条候选 artifact 并抽样复核产地、食品范围、类别、风险标签和官方文本；通过人工验收后，再定义 production 发布门禁。

---

## 2026-06-28 · Round 34 · Taiwan TFDA border noncompliance prototype

### 本轮结果

定位台湾 TFDA 官方“不符合食品資訊資料集”：JSON 直接包含产地、产品、原因、进口商、税则号、检验结果、处置和日期，并采用政府资料开放授权条款第 1 版。

2026-06-28 官方 JSON 共 2,472 条，日期范围 2023-01-03 至 2026-06-23；中国大陆/中国来源 576 条。按税则第 01–24 章、排除第 23 章饲料及明确容器具原因后，384 条为中国来源可食用候选。

### 本轮改动

- 新增 `probe-taiwan-tfda`、解析器与稳定项目 ID；
- 增加字段、日期、重复 ID、总记录数和中国记录数门禁；
- 新增每周/手动只读 GitHub Action 和 artifact；
- 新增 6 项单元测试与 `docs/SOURCE_TAIWAN.md`；
- 台湾从 `candidate` 升为只读 `prototype`，不写入 `data/processed/`。

首次真实验收发现少数字段组合会产生 147 个 ID 碰撞；由于官方数据没有原生行 ID，现改为对完整规范化官方记录做 canonical JSON SHA-256，2,472 条记录碰撞数降为 0。

### 下一步

提交后手动运行 `Probe Taiwan TFDA source`。通过后继续设计台湾增量 baseline 与 candidate 管线。

### 验证结果

- 全套 97 项单元测试通过；
- 真实官方 JSON probe 通过：2,472 条总记录、576 条中国来源、384 条中国可食用候选、0 个重复 ID、0 个日期错误；
- `git diff --check` 通过（仅有 Windows LF/CRLF 提示）。

---

## 2026-06-28 · Round 33 · Korea GitHub Runner timeout hardening

### 故障

首次 `Probe Korea Food Safety source` GitHub Actions 在列表阶段失败：Python `urllib` 对一次请求 400 条记录的官方 portal POST 超时，未进入 JSON 解析或详情验证。

### 本轮修复

- 韩国网络层由 `urllib` 改为参数数组调用 curl；
- 强制 IPv4 与 HTTP/1.1，设置连接/总超时、三次 `--retry-all-errors`、User-Agent、Referer 和 AJAX header；
- 列表发现从单次 400 条改为“最新 60 条 + `중국산` 产品名专项搜索”；
- 两份官方响应按 `rtrvldsuse_seq` 去重合并，仍优先抽取中国来源；
- 报告新增 discovery mode、最新列表返回数和中国专项搜索计数；
- 增加 curl 参数和双列表合并回归测试。

### 状态边界

本次只修复 GitHub Runner 网络可靠性，不降低最低 1 条中国来源门槛，也不改变韩国 `candidate` 状态。

### 验证说明

受管桌面 sandbox 会把子进程 curl 指向不可用的本地代理，因此默认联网命令在该 sandbox 内不能作为验收依据；同样的官方 POST 使用获准的外部 curl 已成功返回数据。最终效果需由下一次 GitHub Actions run 验证。

### 验证结果

- 全套 91 项单元测试通过；
- curl 的 IPv4、HTTP/1.1、重试和表单参数有独立回归测试；
- 最新列表与中国专项搜索的去重合并有独立回归测试；
- `git diff --check` 通过（仅有 Windows LF/CRLF 提示）。

### 下一步建议

提交并重新手动运行 `Probe Korea Food Safety source`；若仍超时，保存新 artifact，下一步将固定详情健康检查与列表覆盖检查拆成独立步骤。

后续结果：修复提交后的 GitHub Actions 手动运行已由维护者确认通过。

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
