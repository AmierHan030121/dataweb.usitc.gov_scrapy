# USITC DataWeb 美国进出口月度数据下载脚本

这个项目默认使用 Python + Playwright 控制真实浏览器，复刻 DataWeb 页面手动下载流程。当前默认不再按 `HTS01~HTS99` 拆分，而是每个贸易类型、每个数据指标、每个月下载一张完整 Excel。脚本会优先选择 HTS-10；如果 DataWeb 当前页面没有 HTS-10 选项，则自动改用页面支持的 HTS-6，并在 `logs/manifest.csv` 的 `message` 字段记录。

下载页面：

```text
https://dataweb.usitc.gov/trade/search/Import/HTS
```

## 默认页面配置

- Step 1：按任务选择贸易类型，Classification System 固定为 `HTS Items`
- Step 2：每次只选择一个数据指标、一个月份、`Monthly`
- Step 3：`Use All Countries` + `Display Countries Separately`
- Step 4：`Use All Commodities` + `Display Commodities Separately` + 优先 `HTS-10`，没有 `HTS-10` 时自动使用 `HTS-6`
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
  retries: 8
  retry_sleep_seconds: 30
  form_settle_seconds: 5
  task_sleep_seconds: 60
  restart_browser_on_error: true
  browser_cooldown_seconds: 60
```

`download_timeout_seconds` 建议大于手工下载耗时。你手工验证约 90 秒，默认设置为 360 秒。`retries` 是单个文件最多尝试次数，默认 8 次，用于处理 DataWeb 偶发的页面超时、网络变化、下载未触发和高负载错误。

`form_settle_seconds` 是每个任务完成 Step 1-10 参数设置后、点击 `Download Data` 前的等待时间。`task_sleep_seconds` 是一个真实下载任务结束后、进入下一个任务前的等待时间。批量下载多个月份时建议保持较保守节奏，例如 `form_settle_seconds: 5`、`task_sleep_seconds: 60`，降低被 DataWeb/Akamai 限流的概率。

如果出现 `Due to current high volume`、`Access Denied`、`0 Unknown Error`、`net::ERR_TIMED_OUT`、下载超时等可恢复错误，且 `restart_browser_on_error: true`，脚本会关闭当前自动浏览器，等待 `browser_cooldown_seconds` 秒，然后重新打开浏览器重试当前文件，直到该文件成功或达到 `retries` 上限。

## 30 万行限制

默认不拆 HTS，因为手工验证表明页面全量 HTS-10 下载可以成功。如果后续某个文件下载失败，或者下载后行数超过 30 万，再把 HTS2 拆分作为备用策略单独启用。

注意：Trade Balance 页面可能不提供 HTS-10 选项。脚本会先尝试 HTS-10，发现页面不可用后自动选择 HTS-6；这属于 DataWeb 页面选项限制，不是下载报错。

## 输出和日志

- `downloads/`：下载后的 Excel
- `logs/manifest.csv`：每个任务的状态、路径、行数估算
- `logs/*.error.json`：旧 API 诊断模式产生的错误响应文件
- `output/`：诊断和 dry-run 过程中的辅助文件
