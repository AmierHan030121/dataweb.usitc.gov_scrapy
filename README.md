# USITC DataWeb 美国进出口月度数据下载脚本

这个项目默认使用 Python + Playwright 控制真实浏览器，复刻 DataWeb 页面手动下载流程。当前默认不再按 `HTS01~HTS99` 拆分，而是每个贸易类型、每个数据指标、每个月下载一张完整 HTS-10 Excel。

下载页面：

```text
https://dataweb.usitc.gov/trade/search/Import/HTS
```

## 默认页面配置

- Step 1：按任务选择贸易类型，Classification System 固定为 `HTS Items`
- Step 2：每次只选择一个数据指标、一个月份、`Monthly`
- Step 3：`Use All Countries` + `Display Countries Separately`
- Step 4：`Use All Commodities` + `Display Commodities Separately` + `HTS-10`
- Step 4：如果出现 `Show Details`，脚本会尝试取消勾选
- Step 9：`Combine Rows Onto One Sheet` + `Export Full Data`
- Step 10：`No conversion`
- Step 11：点击 `Download Data` 并等待浏览器下载完成

## 默认任务数

`configs/default.yaml` 默认下载 2026 年 4 月全部配置项，共 23 个文件：

- Import General：5
- Import For Consumption：8
- Export Total：3
- Export Domestic：3
- Export Foreign：3
- Trade Balance：1

## 文件命名

格式：

```text
进出口类型_数据类型_金额或数量种类_YYYYMM.xlsx
```

示例：

```text
IMP_General_Customs_202604.xlsx
IMP_General_CIF_202604.xlsx
IMP_Consumption_Customs_202604.xlsx
EXP_Total_FAS_202604.xlsx
BAL_TradeBalance_FASMinusGenCustoms_202604.xlsx
```

## 安装

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
```

## 运行

先 dry-run 查看将要下载的任务：

```powershell
python -m usitc_dataweb --config configs/default.yaml --dry-run
```

小规模真实下载测试，只下载一个文件：

```powershell
python -m usitc_dataweb --config configs/sample_small.yaml --limit 1
```

完整下载 202604：

```powershell
python -m usitc_dataweb --config configs/default.yaml
```

## 运行参数

- `--config`：指定 YAML 配置文件
- `--dry-run`：只列出任务，不打开浏览器
- `--limit N`：最多执行 N 个任务，用于测试

浏览器配置在 YAML 的 `runtime` 中：

```yaml
runtime:
  timeout_seconds: 60
  download_timeout_seconds: 360
  headless: false
  skip_existing: true
  retries: 2
  retry_sleep_seconds: 30
```

`download_timeout_seconds` 建议大于手工下载耗时。你手工验证约 90 秒，默认设置为 360 秒。`retries` 是单个文件的任务级重试次数，用于处理 DataWeb 偶发的页面超时、网络变化和下载未触发。

## 30 万行限制

默认不拆 HTS，因为手工验证表明页面全量 HTS-10 下载可以成功。如果后续某个文件下载失败，或者下载后行数超过 30 万，再把 HTS2 拆分作为备用策略单独启用。

## 输出和日志

- `downloads/`：下载后的 Excel
- `logs/manifest.csv`：每个任务的状态、路径、行数估算
- `logs/*.error.json`：旧 API 诊断模式产生的错误响应文件
- `output/`：诊断和 dry-run 过程中的辅助文件
