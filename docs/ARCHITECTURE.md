# Architecture

## MVP 纵向切片

```text
FDA 官方 ZIP/CSV
      |
      v
下载与校验 -> 原始行解析 -> 中国记录过滤 -> 原因代码关联
                                      |
                                      v
                              统一字段与风险标签
                                      |
                                      v
                              JSONL / 后续数据库
```

先完成一条真实数据源的端到端链路，再扩展国家/地区。这样可以尽早暴露编码、缺失字段、重复记录、来源变更和法律边界问题。

## 分层

- **Source adapter**：只理解某个官方来源的下载、分页和原始字段。
- **Normalizer**：将原始记录转换为统一契约，不丢失来源标识。
- **Classifier**：用版本化确定性规则生成检索标签；标签不是监管结论。
- **Validator**：验证必填字段、日期、枚举和值域。
- **Publisher**：写入 JSONL；后续可增加 SQLite、Parquet、API 和静态网站。

## Agent、爬虫和 skills 的位置

| 方案 | 现在是否优先 | 合适用途 |
|---|---:|---|
| 数据适配器/采集器 | 是 | 稳定获得官方数据并标准化 |
| HTML 爬虫 | 按来源使用 | 官方没有 API 或下载文件时解析页面 |
| AI Agent | 否 | 监控失败、提出翻译/分类候选、组织人工复核 |
| Agent skill | 否 | 数据接口稳定后，对外提供查询与解释能力 |

## 统一记录设计原则

- 行为类型分开：进口拒绝、召回、警报、检测不合格不能混为一个结论。
- 机构地区与产品来源分开：`authority_region` 不等于 `origin_country`。
- 产品来源与监管市场分开：`origin_country` 不明确时保留 `unknown`；境内抽检使用 `regulatory_scope: domestic_market` 与 `market_country: CN`，不能据生产商、进口商或代理地址反推原产地。
- 原始原因与项目标签分开：`reasons` 保存监管文本，`hazard_tags` 用于筛选。
- 每条记录带 `source_url`、`source_record_id` 和 `retrieved_at`。
- 稳定 ID 根据来源与来源记录标识生成，支持重复运行去重。

## 接入顺序建议

按“机器可读性 + 消费者价值”排序，而不是一次接入所有地区：

1. FDA Import Refusals：官方 ZIP/CSV，历史长，适合建立基线。
2. FSANZ 召回：已建立 sitemap + HTML 解析原型；通过真实页面生产门禁后启用。
3. 欧盟 RASFF：价值高，但需要先确认公开接口、使用条款和字段语义。
4. 其余地区逐一做 source spike，记录访问方式、更新频率、许可和反自动化限制。

## 下一里程碑

M1 的完成标准：一次命令可获取 FDA 当前数据包，筛选中国记录，输出通过 schema 检查的 JSONL，并有固定样本测试、数据质量摘要和 GitHub Actions 定时运行。
