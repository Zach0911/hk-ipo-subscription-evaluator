# hk-ipo-subscription-evaluator

港股 IPO 申购期打新评估 skill，用于在新股仍处于公开发售/申购窗口时，辅助判断是否参与港股 IPO 申购。

结论只落到三档之一：

- 参与
- 低仓位参与
- 不参与

本项目不是上市后交易复盘工具，也不是收益预测工具。它只服务于“申购期是否参与”的决策整理。

## 适用场景

适合用于：

- 港股打新、港股 IPO 申购、新股申购分析
- 判断某只港股 IPO 是否仍在申购期
- 对比发行条款、基石投资者、保荐人、募资用途和申购热度
- 参考近 1 年同类港股 IPO 的首日、5 日、20 日表现
- 输出可复用的结构化申购建议

不适合用于：

- 暗盘交易策略
- 配发结果复盘
- 上市首日或上市后交易建议
- 长期个股投资研究
- 用最终认购倍数、中签率或上市表现倒推申购期结论

## 目录结构

```text
hk-ipo-subscription-evaluator/
  SKILL.md
  README.md
  data/
    hk_ipo_history.csv
    hkex_current_new_listings.csv
  references/
    data-sources.md
    historical-peer-ipo.md
    output-template.md
    scoring-rubric.md
  scripts/
    build_hk_ipo_history.py
    enrich_ipo_returns.py
    fetch_hkex_ipo_list.py
    finance_all_in_one_adapter.py
    match_peer_ipos.py
    update_hk_ipo_history.py
```

## 核心流程

1. 确认标的、代码、招股书和是否仍在申购期。
2. 收集发行价、发行市值、募资规模、每手金额、公开发售比例、回拨机制、基石投资者和保荐人。
3. 阅读招股书中的业务、财务、现金流、客户/供应商集中度、募资用途和主要风险。
4. 收集申购期阶段性孖展或认购热度。
5. 匹配近 1 年同类型、同板块、同行业港股 IPO 历史样本。
6. 统计同类样本首日、5 日、20 日表现和破发率。
7. 按 100 分模型评分。
8. 输出三档结论，并说明为什么不是更高或更低一档。

## 评分模型

总分 100 分：

| 维度 | 权重 |
|---|---:|
| 当前 IPO 基本面质量 | 20 |
| 发行估值与安全边际 | 20 |
| 近 1 年同类 IPO 历史表现 | 20 |
| 发行结构与筹码质量 | 15 |
| 申购期市场热度与资金效率 | 10 |
| 保荐人与承销质量 | 10 |
| 当前市场窗口 | 5 |

三档判断：

| 档位 | 参考条件 |
|---|---|
| 参与 | 总分 >= 75，且无重大红旗 |
| 低仓位参与 | 总分 55-74，或亮点与不确定性并存 |
| 不参与 | 总分 < 55，或出现重大红旗 |

完整规则见 [references/scoring-rubric.md](references/scoring-rubric.md)。

## 数据边界

申购期核心输入：

- 招股书/聆讯后资料集
- 发行价区间、发行市值、募资规模、每手金额
- 公开发售比例、国际配售比例、回拨机制
- 基石投资者、保荐人、承销商
- 募资用途、盈利状态、现金流、客户/供应商集中度
- 申购期阶段性孖展/认购热度
- 近 1 年同类型、同板块、同行业港股 IPO 上市表现

不作为申购期核心输入：

- 暗盘表现
- 最终认购倍数
- 中签率/分配结果
- 上市首日涨跌
- 上市后 5 日或 20 日走势

这些数据只能用于历史样本库、申购后复核或上市后分析，不能倒推当前申购期结论。

## 常用脚本

在 skill 根目录运行：

```bash
python3 scripts/fetch_hkex_ipo_list.py --board all
```

抓取 HKEX 当前 Main Board/GEM 新上市信息，默认写入：

```text
data/hkex_current_new_listings.csv
```

创建空白历史样本库：

```bash
python3 scripts/build_hk_ipo_history.py
```

导入外部整理好的历史样本：

```bash
python3 scripts/update_hk_ipo_history.py --input new_rows.csv
```

用本地金融数据能力补齐历史样本收益：

```bash
python3 scripts/enrich_ipo_returns.py --data data/hk_ipo_history.csv
```

匹配近 1 年同类 IPO：

```bash
python3 scripts/match_peer_ipos.py \
  --industry "医疗器械" \
  --sector "医疗保健" \
  --market-cap-hkd-m 8000 \
  --fundraising-hkd-m 1200 \
  --profit-status "盈利" \
  --valuation-type "PE"
```

## 历史样本库字段

`data/hk_ipo_history.csv` 使用以下字段：

```text
company_name,code,listing_date,industry,sector,business_model,listing_type,
issue_price_hkd,market_cap_hkd_m,fundraising_hkd_m,profit_status,growth_stage,
valuation_type,valuation_multiple,sponsor,cornerstone_investors,
public_subscription_multiple,one_lot_success_rate,first_day_return_pct,
day5_return_pct,day20_return_pct,is_broken,notes,source_url,source_date
```

## 标准输出

每次完整评估应包含：

- 结论档位
- 一句话理由
- 置信度
- 当前 IPO 关键信息
- 评分表
- 近 1 年同类 IPO 历史表现摘要
- 核心依据
- 主要风险
- 现金/融资申购建议
- 数据缺口
- 来源

输出模板见 [references/output-template.md](references/output-template.md)。

## 示例提问

```text
[$hk-ipo-subscription-evaluator] 分析天辰生物-B，代码01779
```

```text
[$hk-ipo-subscription-evaluator] 分析大金重工
```

如果用户没有提供申购方式和资金约束，可以先按“一手/小额现金申购”的保守口径输出，并在数据缺口中标注。

## 风险提示

本 skill 仅用于结构化整理港股 IPO 申购期信息，不构成投资建议，不承诺收益，不代替用户下单。涉及实时发行、认购和市场数据时，必须标注数据日期和来源；数据不足时可以给临时倾向，但必须降低置信度并列出待补信息。
