# 近 1 年同类 IPO 历史样本

## 目标

评估当前港股 IPO 的申购收益风险比，必须参考近 1 年同类型、同板块、同行业港股 IPO 的上市表现。

默认口径：

- 时间窗口：过去 12 个月。
- 市场：港股 IPO。
- 默认排除：SPAC、介绍上市、二次上市、由介绍方式上市的项目。
- 若用户明确要求，可单独纳入特殊上市类型，但必须分组展示。

## 本地样本库与脚本

本 skill 提供一个本地样本库和三个脚本：

```text
data/hk_ipo_history.csv
data/hkex_current_new_listings.csv
scripts/build_hk_ipo_history.py
scripts/update_hk_ipo_history.py
scripts/fetch_hkex_ipo_list.py
scripts/finance_all_in_one_adapter.py
scripts/enrich_ipo_returns.py
scripts/match_peer_ipos.py
```

优先运行 `scripts/match_peer_ipos.py` 获取近 1 年同类样本统计。

更新当前 HKEX 新上市信息：

```bash
python scripts/fetch_hkex_ipo_list.py --board all
```

用 `finance-all-in-one` 补齐历史样本收益：

```bash
python scripts/enrich_ipo_returns.py --data data/hk_ipo_history.csv
```

常用命令：

```bash
python scripts/match_peer_ipos.py \
  --industry "医疗器械" \
  --sector "医疗保健" \
  --market-cap-hkd-m 8000 \
  --fundraising-hkd-m 1200 \
  --profit-status "盈利" \
  --valuation-type "PE"
```

导入外部 CSV：

```bash
python scripts/update_hk_ipo_history.py --input /path/to/new_rows.csv
```

如果 `data/hk_ipo_history.csv` 为空、过旧或样本不足，必须说明数据缺口，并使用联网检索或请用户补充历史样本。

## 样本匹配顺序

按以下顺序筛选：

1. 同行业/同板块。
2. 商业模式相近。
3. 发行市值接近，优先当前 IPO 市值的 0.5x-2x 区间。
4. 盈利状态相同：盈利、亏损、未商业化分别匹配。
5. 成长阶段相近：成熟稳定、成长扩张、早期投入。
6. 发行规模接近。
7. 估值方式一致：PE、PS、EV/Sales、管线估值等。
8. 保荐人/承销商相同或历史质量相近。
9. 市场窗口相近：同期香港恒指、恒生科技、新股破发率环境。

## 样本字段

每个样本尽量收集：

| 字段 | 说明 |
|---|---|
| 公司名/代码 | 历史 IPO 标的 |
| 上市日期 | 确认是否在近 1 年窗口内 |
| 行业/板块 | 匹配依据 |
| 发行价/发行市值 | 估值对比 |
| 募资规模 | 发行规模对比 |
| 盈利状态 | 盈利、亏损、未商业化 |
| 发行估值 | PE/PS/EV/Sales 等 |
| 保荐人 | 承销质量对比 |
| 基石投资者 | 机构质量与锁定情况 |
| 公开发售认购倍数 | 历史热度指标 |
| 一手中签率 | 资金效率指标 |
| 首日涨跌幅 | 打新收益核心指标 |
| 首 5 日涨跌幅 | 短线资金延续性 |
| 首 20 日涨跌幅 | 板块承接能力 |
| 是否破发 | 风险标签 |
| 不可比因素 | 极端行情、特殊事件、样本异常 |

`data/hk_ipo_history.csv` 使用以下字段：

```text
company_name,code,listing_date,industry,sector,business_model,listing_type,issue_price_hkd,market_cap_hkd_m,fundraising_hkd_m,profit_status,growth_stage,valuation_type,valuation_multiple,sponsor,cornerstone_investors,public_subscription_multiple,one_lot_success_rate,first_day_return_pct,day5_return_pct,day20_return_pct,is_broken,notes,source_url,source_date
```

## 统计指标

至少输出：

- 样本数量
- 样本匹配质量：高/中/低
- 首日正收益率
- 首日收益中位数
- 首日破发率
- 首 5 日收益中位数
- 首 20 日收益中位数
- 当前 IPO 估值相对样本的分位或相对位置

如果数据允许，补充：

- 一手中签率中位数
- 认购倍数与首日表现关系
- 同保荐人项目破发率
- 同板块过去 3 个月新股窗口变化

## 样本数量处理

| 样本数量 | 处理方式 |
|---|---|
| >= 8 个高度相似样本 | 可作为核心证据 |
| 4-7 个相似样本 | 可作为重要参考，但提示样本有限 |
| 1-3 个相似样本 | 只能作为案例参考，不能单独支撑结论 |
| 0 个相似样本 | 改用更宽口径板块样本，并显著降低置信度 |

## 输出注意事项

不要把“不同行业但同样热门”的 IPO 当作高度可比样本。

不要只列最成功案例。必须同时展示破发或表现较弱样本，否则容易高估打新收益。

如果当前 IPO 是稀缺标的，仍要说明稀缺性不能完全替代历史样本验证。
