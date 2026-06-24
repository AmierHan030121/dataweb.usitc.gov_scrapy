# USITC DataWeb Browser Download Redesign

## Goal

Use Python browser automation to reproduce the successful manual DataWeb download flow for April 2026 monthly HTS-10 data, then rename each downloaded Excel file according to the project naming rule.

## Confirmed Manual Flow

- Open `https://dataweb.usitc.gov/trade/search/Import/HTS`.
- Step 1 sets the trade flow and classification system.
- Step 2 sets one data measure, one month, and monthly aggregation.
- Step 3 uses all countries and selects `Display Countries Separately`.
- Step 4 uses all commodities, selects `Display Commodities Separately`, selects `HTS-10`, and disables `Show Details` if it appears.
- Step 9 enables `Combine Rows Onto One Sheet` and `Export Full Data`.
- Step 10 uses `No conversion`.
- Step 11 clicks `Download Data` and waits for the browser download to complete.

## Default Scope

For a single month, generate one full download task per flow and measure. Do not split by HTS2 by default.

- Import General: 5 measures.
- Import For Consumption: 8 measures.
- Export Total: 3 measures.
- Export Domestic: 3 measures.
- Export Foreign: 3 measures.
- Trade Balance: 1 measure.

Total default tasks for one month: 23.

## File Names

Downloaded files are renamed to:

```text
{flow_prefix}_{measure_label}_{yyyymm}.xlsx
```

Examples:

```text
IMP_General_Customs_202604.xlsx
IMP_General_CIF_202604.xlsx
EXP_Total_FAS_202604.xlsx
BAL_TradeBalance_FASMinusGenCustoms_202604.xlsx
```

## Error Handling

- The browser download timeout defaults to 240 seconds.
- Existing files are skipped when `skip_existing` is true.
- A manifest row is written for each task.
- Browser automation failures are logged and the runner continues to the next task.
- HTS2 splitting remains a future fallback only when a full download fails or when a file exceeds the 300,000-row warning threshold.

