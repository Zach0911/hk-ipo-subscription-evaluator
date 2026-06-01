---
name: hk-ipo-subscription-evaluator
description: Use when evaluating whether to subscribe to a Hong Kong IPO during its subscription period, including 港股打新, 港股 IPO 申购, 新股申购, and requests for 参与/低仓位参与/不参与 conclusions.
---

# 港股 IPO 申购期打新评估

## 核心原则

这是“申购期是否参与港股 IPO 打新”的决策 skill。结论必须落到三档之一：

- 参与
- 低仓位参与
- 不参与

不要把它写成上市后交易复盘、暗盘策略或长期个股研究。

## 先确认

开始前先确认四类信息；缺失时先补充检索或向用户追问：

- 标的：公司名、代码、招股/申购链接或招股书。
- 时点：是否仍处于申购期。
- 方式：现金申购还是融资申购。
- 约束：用户资金规模、风险偏好、是否只考虑一手。

如果已过申购期，不输出“是否申购”的假结论；改为说明“已过申购窗口，可做上市前复核、暗盘观察或上市后交易评估”。

## 数据边界

申购期核心输入：

- 招股书/聆讯后资料集
- 发行价区间、发行市值、募资规模、每手金额
- 公开发售比例、国际配售比例、回拨机制
- 基石投资者、保荐人、承销商
- 募资用途、盈利状态、现金流、客户/供应商集中度
- 申购期阶段性孖展/认购热度
- 近 1 年同类型、同板块、同行业港股 IPO 上市表现

不能作为申购期核心输入：

- 暗盘表现
- 最终认购倍数
- 中签率/分配结果
- 上市首日涨跌
- 上市后 5 日或 20 日走势

这些数据只能用于历史样本库、申购后复核或上市后分析，不能倒推当前申购期结论。

## 必须读取的参考文件

根据任务读取对应文件：

- 评分和三档结论：读 `references/scoring-rubric.md`
- 数据来源和检索顺序：读 `references/data-sources.md`
- 近 1 年同类 IPO 样本：读 `references/historical-peer-ipo.md`
- 输出格式：读 `references/output-template.md`

## 可用脚本

优先使用本地历史样本库和脚本，路径相对 skill 根目录：

- `data/hk_ipo_history.csv`：港股 IPO 历史样本库。
- `data/hkex_current_new_listings.csv`：HKEX 当前 Main Board/GEM 新上市信息快照。
- `scripts/fetch_hkex_ipo_list.py`：抓取 HKEX 当前新上市信息表，包含代码、公司名、公告/招股书/配发结果链接。
- `scripts/finance_all_in_one_adapter.py`：调用 `finance-all-in-one` 获取港股 K 线、行情、估值。
- `scripts/enrich_ipo_returns.py`：用 `finance-all-in-one` 港股 K 线补齐历史样本首日、5 日、20 日收益和是否破发。
- `scripts/match_peer_ipos.py`：按行业、板块、市值、盈利状态等匹配近 1 年同类 IPO，并输出统计摘要。
- `scripts/update_hk_ipo_history.py`：把外部整理好的 CSV 合并进历史样本库。
- `scripts/build_hk_ipo_history.py`：创建空白历史样本库模板。

示例：

```bash
python scripts/fetch_hkex_ipo_list.py --board all
python scripts/enrich_ipo_returns.py --data data/hk_ipo_history.csv
python scripts/match_peer_ipos.py \
  --industry "医疗器械" \
  --sector "医疗保健" \
  --market-cap-hkd-m 8000 \
  --profit-status "盈利" \
  --valuation-type "PE"
```

如果样本库为空或匹配样本不足，再使用联网检索、本地金融数据 skill，或请用户提供历史样本。

## 标准流程

1. 确认是否仍在申购期。
2. 优先运行 `scripts/fetch_hkex_ipo_list.py` 获取 HKEX 当前新上市/申购相关信息，再收集当前 IPO 发行信息和招股书核心事实。
3. 如历史样本缺少上市后收益，先运行 `scripts/enrich_ipo_returns.py` 用 `finance-all-in-one` 港股 K 线补齐。
4. 优先调用 `scripts/match_peer_ipos.py` 建立近 1 年同类 IPO 历史样本，匹配同行业、同板块、同市值、同盈利状态。
5. 统计同类样本首日、5 日、20 日表现和破发率。
6. 按 100 分模型评分。
7. 输出三档结论，并说明为什么不是更高或更低一档。
8. 标注数据缺口和置信度。

## 输出要求

每次标准输出必须包含：

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

## 风险提示

不要承诺收益。不要代替用户下单。涉及实时发行、认购和市场数据时，必须标注数据日期和来源。数据不足时可以给“临时倾向”，但必须降低置信度并列出待补信息。
