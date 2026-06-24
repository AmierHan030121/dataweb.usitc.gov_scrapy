# USITC DataWeb 美国进出口月度数据下载脚本

这个项目用 Python 直接调用 DataWeb 前端使用的接口，不依赖人工点击页面。已确认的下载接口是：

- 页面：`https://dataweb.usitc.gov/trade/search/Import/HTS`
- API：`https://datawebws.usitc.gov/dataweb/api/v2/report2/dataExport`

## 默认抓取规则

- Classification System：`HTS`
- Timeframe Option：`Custom Time Period and Years`
- Timeframe Aggregation：`Monthly`
- 每次只选择一个月份、一个金额或数量指标
- Countries：`Use All Countries` + `Display Countries Separately`
- Commodities：`Use All Commodities` + `Display Commodities Separately`
- Commodity Aggregation Level：进口、出口和 Trade Balance 均使用 `HTS-10`
- Programs、Rate Provision Codes、Districts：默认聚合
- Row Options：`Combine rows onto one sheet` 和 `Export Full Data`
- Unit Conversion：`No conversion`

## 文件命名

格式为：

```text
进出口类型_数据类型_金额或数量种类_YYYYMM[_HTSxx].xlsx
```

示例：

```text
IMP_General_CIF_202604_HTS01.xlsx
EXP_Total_FAS_202604_HTS84.xlsx
BAL_TradeBalance_FASMinusGenCustoms_202604_HTS01.xlsx
```

默认开启 HTS2 拆分，所以会追加 `_HTSxx`。如果关闭拆分，会生成类似 `IMP_General_CIF_202604.xlsx` 的文件名。

## 安装

```powershell
python -m pip install -r requirements.txt
```

## 运行

小验证，只下载 General Import 的 CIF、2026 年 4 月、HTS01：

```powershell
python -m usitc_dataweb --config configs/sample_small.yaml
```

完整配置：

```powershell
python -m usitc_dataweb --config configs/default.yaml
```

只生成 payload、不实际下载：

```powershell
python -m usitc_dataweb --config configs/default.yaml --dry-run
```

临时关闭 HTS2 拆分：

```powershell
python -m usitc_dataweb --config configs/sample_small.yaml --no-split
```

## 30 万行限制处理

DataWeb 单张表数据量过大时容易失败。脚本默认按 HTS2 章节拆分：

```yaml
split:
  strategy: hts2
  hts2_chapters: ["01", "02", "...", "99"]
```

如果某个 HTS2 章节仍然过大，可以把 `hts2_chapters` 进一步拆成更细的 HTS4 前缀后扩展 `build_payload` 的 `hts_prefix` 逻辑；当前 DataWeb payload 已经按“选择个别商品代码”的方式组织，支持继续细分。

## 日志和诊断

- `downloads/`：下载的 Excel
- `output/payloads/`：每个请求的 JSON payload
- `logs/manifest.csv`：每个任务的状态、路径、行数估算
- `logs/*.error.json`：接口失败时保存 HTTP 状态、响应头和响应体

如果下载端点处于维护期，脚本会停止并在 manifest 中记录 `maintenance`。本次开发验证时，`getGlobalVars` 可访问，但 `dataExport` 返回了 DataWeb 的维护页。
