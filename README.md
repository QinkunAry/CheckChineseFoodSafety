# Food Safety Watch / 食安观察

[![CI](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/ci.yml/badge.svg)](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/ci.yml)
[![Update FDA data](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/update-fda.yml/badge.svg)](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/update-fda.yml)
[![Smoke test Japan CAA source](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/smoke-japan-caa.yml/badge.svg)](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/smoke-japan-caa.yml)
[![Probe Korea Food Safety source](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/probe-korea-recalls.yml/badge.svg)](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/probe-korea-recalls.yml)
[![Probe Taiwan TFDA source](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/probe-taiwan-tfda.yml/badge.svg)](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/probe-taiwan-tfda.yml)
[![Update Taiwan TFDA data](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/update-taiwan-tfda.yml/badge.svg)](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/update-taiwan-tfda.yml)
[![Probe China SAMR source](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/probe-china-samr.yml/badge.svg)](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/probe-china-samr.yml)
[![Probe EU RASFF source](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/probe-rasff.yml/badge.svg)](https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/probe-rasff.yml)

一个以官方证据为核心的开源食品安全数据项目。它定期收集境外监管机构发布的进口拒绝、召回和安全警报，也研究中国境内官方抽检不合格信息；所有范围保留原始出处并转换为可区分监管语境的统一记录。

GitHub 仓库：[QinkunAry/CheckChineseFoodSafety](https://github.com/QinkunAry/CheckChineseFoodSafety)

> 本项目提供监管信息聚合，不进行医学诊断、实验室检测或“某食品一定安全/有毒”的判断。

完整产品方向见 [`PRODUCT_GOALS.md`](PRODUCT_GOALS.md)，每轮开发过程见 [`DEVELOPMENT_LOG.md`](DEVELOPMENT_LOG.md)。
各监管数据来源的授权和署名见 [`docs/DATA_ATTRIBUTION.md`](docs/DATA_ATTRIBUTION.md)。

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

## 数据边界

- `import_refusal` 不等于召回，也不表示同类产品全部存在风险。
- `origin_country` 在 FDA 数据中来自申报制造商所在国家/地区，不能自动推断品牌国籍或全部原料产地。
- 风险标签是便于检索的项目分类，监管机构原始原因文本始终优先。
- 中文翻译在进入事实字段前应经过人工或可追踪的审核流程。
- `prototype` 来源只能生成 smoke、inventory 和 candidate artifact；只有通过发布前 checklist 后，才允许写入 `data/processed/`。

## 项目结构

```text
data/sources.json          数据源登记表
data/state/                来源增量状态（非监管事实）
data/candidates/           候选记录产物（不等于正式发布数据）
schemas/record.schema.json 统一记录契约
src/food_safety_watch/     采集与标准化代码
tests/                     单元测试
docs/ARCHITECTURE.md       架构和路线图
docs/DATA_ATTRIBUTION.md   监管数据授权与署名
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

`.github/workflows/smoke-fsanz.yml` 每周只读检查 FSANZ 官方 sitemap 和固定召回详情，验证页面证据字段，并对实际发现的中国原产记录执行统一 Schema 检查。固定样本中没有中国记录会被报告，但不再误判为站点结构故障。它不会提交或发布 FSANZ 数据；通过覆盖率评估和再利用条款检查前，该来源保持 `prototype`。

同一工作流还会把官方 sitemap 与 `data/state/fsanz_recall_urls.json` 中的 345 条基线比较，只报告新增和移除的详情 URL。该基线用于避免未来重复扫描全部历史页面，不代表 345 条记录都属于中国食品或都已进入发布数据集。

当官方 sitemap 出现新增详情 URL 时，`candidate-fsanz` 只抓取这些新增页面，生成 `data/candidates/fsanz_cn.jsonl` 和 `reports/fsanz_candidates.json` 作为 artifact。候选记录用于人工复核 parser、版权/再利用边界和数据质量；在来源状态仍为 `prototype` 时，它不会合并进正式发布数据。

`.github/workflows/smoke-cfs.yml` 每周只读检查香港 CFS Food Alerts / Allergy Alerts 年度列表和固定详情页，验证 `Issue Date`、`Food Product`、`Place of origin` 和 `Reason For Issuing Alert` 字段，并对中国原产记录执行统一 Schema 检查。CFS 当前也保持 `prototype`，不会提交或发布正式数据。

同一工作流还会把 CFS 当前年度列表与 2025 年列表中的官方详情 URL 和 `data/state/cfs_alert_urls.json` 基线比较，只报告新增和移除 URL。该基线当前覆盖 36 条 alert URL，不代表 36 条都属于中国食品或已进入正式数据集。

当 CFS 官方列表出现新增详情 URL 时，`candidate-cfs` 只抓取这些新增页面，在 runner 内生成 `data/candidates/cfs_cn.jsonl` 和 `reports/cfs_candidates.json`。在 CFS 授权边界明确前，workflow 只上传诊断报告 artifact，不上传候选 JSONL；候选记录不会自动合并进正式发布数据。

CFS 的官方版权声明要求获得食物环境卫生署事先书面授权后，才可复制、分发、传播或公开提供其版权作品。因此在授权或等效复用依据记录前，CFS 保持 `prototype`；workflow 只上传最小诊断报告，不上传包含官方原因文本的候选 JSONL。

加拿大 Recalls and Safety Alerts 当前保持 `candidate`。官方 open data 提供每日更新的 JSON/CSV/RSS，并使用 Open Government Licence - Canada；但已观察到的 open-data 字段和样本详情页没有稳定原产地字段，因此在找到明确 origin evidence 前不能发布中国来源记录。详见 `docs/SOURCE_CANADA.md`。

可用 `probe-canada-origin` 做只读抽样诊断。2026-06-24 的真实 probe 显示：33,692 条全类别记录中有 5,243 条 CFIA 食品记录，open data 中 12 条 CFIA 食品记录提到 China/Chinese；抽样 32 个详情页后，仍没有发现明确中国原产地证据。

欧盟 RASFF 已升级为只读 `prototype`。`probe-rasff` 已在 GitHub Actions 通过：它从 RASFF Window 官方目录动态取得国家和产品类型 ID，以 `originCountry=CN` 与 `notificationType=food` 双条件查询，并用印度人类食品作为非中国对照。`inventory-rasff` 完整扫描 13 页并建立 1,211 条 notification baseline，只保存官方 ID、reference 和选定字段指纹；首次回读为 0 new、0 removed、0 changed。Action 只上传诊断报告，不提交或发布监管记录。详见 `docs/SOURCE_RASFF.md`。

日本 CAA / MHLW 当前为只读 `prototype`。`smoke-japan-caa` 每周固定检查两条中国来源样本和一条非中国对照，扫描 CAA 食料品分页并与 321 条 URL baseline 比较；`candidate-japan-caa` 只解析 baseline 之后的新 URL，跟进 MHLW 参照详情，并生成 ignored candidate JSONL 与诊断报告。工作流不会提交或发布日本数据；升级前仍需要人工复核非空候选批次、生产质量门禁和最终 PDL 1.0 署名文案。详见 `docs/SOURCE_JAPAN.md`。

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
- [x] 完成韩国 Food Safety Korea 来源 probe 与原产地证据评估
- [x] 将台湾 TFDA 边境不合格食品推进到只读 probe prototype
- [x] 为台湾 TFDA 增加增量记录基线与候选 JSONL 管线
- [x] 将台湾 TFDA 升级为 implemented 正式数据源
- [x] 完成中国大陆 SAMR 公告与 XLSX/ZIP 只读 source probe
- [x] 为中国大陆 SAMR 建立完整分页与 78 条公告 URL baseline
- [x] 为中国大陆 SAMR 实现抽样编号聚合和本地候选复核
- [x] 打通欧盟 RASFF 官方公开 JSON 探针与 China+food 双过滤
- [x] 为欧盟 RASFF 建立完整分页与 1,211 条指纹 baseline
- [ ] 发布静态数据页与筛选界面
- [ ] 按可获取性接入加拿大、日本、韩国、台湾、新西兰和欧盟等来源
- [ ] 在事实层稳定后提供 API / Agent skill
- [ ] 评估 iOS App

## 许可证

代码采用 MIT License。监管数据本身的再利用条件以各来源机构条款为准；发布数据快照前需逐项核对。
