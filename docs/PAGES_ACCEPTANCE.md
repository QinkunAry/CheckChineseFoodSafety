# Hosted GitHub Pages Acceptance Checklist / 线上页面验收清单

本文档用于验收 GitHub Pages 上的静态数据浏览器。它关注公开访问、数据完整性、证据可追溯性和用户误解风险；不替代各数据源的 `SOURCE_*.md`、发布前 checklist 或 operations 文档。

## 入口

- Production site: <https://qinkunary.github.io/CheckChineseFoodSafety/>
- Deployment workflow: <https://github.com/QinkunAry/CheckChineseFoodSafety/actions/workflows/deploy-pages.yml>
- Source repository: <https://github.com/QinkunAry/CheckChineseFoodSafety>

## 每次正式验收前

- [ ] 仓库 visibility 为 public，或当前 GitHub 方案明确支持 private Pages；
- [ ] Settings → Pages → Build and deployment Source 为 GitHub Actions；
- [ ] 最新 `Deploy static data site` workflow 运行成功；
- [ ] workflow 使用当前 `main` 分支 commit；
- [ ] workflow 没有 blocking annotation；
- [ ] 若只有 warning，已判断 warning 不影响页面访问、数据完整性或未来运行时兼容。

## 页面可访问性

- [ ] Production site 可以通过 HTTPS 打开；
- [ ] 首屏标题、说明文字和数据加载状态正常显示；
- [ ] 浏览器刷新后页面仍可打开，不依赖本地开发服务器；
- [ ] 直接访问 `site/data/summary.json` 对应的线上路径能返回 JSON；
- [ ] 直接访问 `site/data/records.json` 对应的线上路径能返回 JSON；
- [ ] 移动端窄屏下页面可读，筛选区域不会遮挡记录列表。

## 数据完整性

- [ ] 页面显示的记录数与 `summary.json` 中的 `record_count` 一致；
- [ ] `records.json` 实际数组长度与 `summary.json.record_count` 一致；
- [ ] `summary.json.missing_files` 为空；
- [ ] 页面只展示 `data/sources.json` 中状态为 `implemented` 的来源；
- [ ] 记录数不低于当前 workflow 的生产门槛；
- [ ] 各 implemented 来源至少有代表性记录可检索到；
- [ ] 页面不展示 `prototype`、`candidate` 或本地人工复核中间产物。

## 筛选与浏览

- [ ] keyword 搜索能匹配产品名、原因、来源或监管文本中的关键词；
- [ ] source 筛选能切换 FDA、Taiwan TFDA、Japan MHLW-backed、EU RASFF 等 implemented 来源；
- [ ] hazard/risk 标签筛选结果与记录标签一致；
- [ ] action type 筛选能区分 import refusal、border rejection、recall、notification 等监管动作；
- [ ] year 筛选能按事件日期或来源日期缩小范围；
- [ ] 清空筛选后记录数量恢复；
- [ ] 空结果状态清楚，不像页面加载失败。

## 证据与出处

- [ ] 抽样检查每个 implemented 来源至少 2 条记录；
- [ ] 每条抽样记录包含官方 source URL；
- [ ] source URL 能打开官方详情、数据页或可追溯的官方端点；
- [ ] 页面保留监管机构原始原因文本或可追溯摘要；
- [ ] `origin_country` 或 `regulatory_scope` 的解释不误导用户；
- [ ] RASFF 记录能区分 active、withdrawn 或需要复核的生命周期状态；
- [ ] 日本记录只展示通过 MHLW detail 支撑的正式发布记录；
- [ ] FDA import refusal 不被页面文案描述成 recall。

## 授权、署名与边界说明

- [ ] 页面或 README 能链接到 `docs/DATA_ATTRIBUTION.md`；
- [ ] 各 implemented 来源的署名、许可和修改说明已经记录；
- [ ] EU RASFF 保留 CC BY 4.0 所需署名和修改声明；
- [ ] 日本 MHLW-backed 数据保留 PDL 1.0 相关出处说明；
- [ ] 页面明确说明本项目是监管信息聚合，不是实验室检测、医疗建议或购买建议；
- [ ] 页面避免暗示监管机构、GitHub 或数据来源方背书本项目。

## 失败处理

- [ ] 若 build/test/site verification 失败，workflow 不部署新的 artifact；
- [ ] 若数据源更新失败，失败报告只作为 artifact 或 Issue，不覆盖已发布数据；
- [ ] 若已发布记录在官方详情中撤回或变化，对应 audit workflow 返回 `action_required` 或 `failed`；
- [ ] 维护者不得直接编辑线上生成文件，应修改源数据、代码或配置后重新部署；
- [ ] 需要回滚时优先使用 GitHub Actions 历史部署或 `git revert` 回滚触发部署的 commit。

## 人工验收标准

一次 hosted Pages 验收可以记为通过，当且仅当：

- [ ] 最新部署 workflow 为 green；
- [ ] production URL 可打开；
- [ ] summary 与 records 数量一致；
- [ ] 至少 8 条跨来源样本通过官方出处复核；
- [ ] 关键筛选器工作正常；
- [ ] 页面文案没有把监管记录解释成超出证据范围的食品安全结论；
- [ ] 新发现问题已记录到 Issue、`DEVELOPMENT_LOG.md` 或下一轮计划。

