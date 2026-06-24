from __future__ import annotations

from .constants import Measure, TradeFlow


def _column(name: str, value: str) -> dict[str, object]:
    return {
        "checked": False,
        "classificationSystem": "",
        "disabled": False,
        "groupUUID": "",
        "hasChildren": False,
        "items": [],
        "name": name,
        "tradeType": "",
        "value": value,
    }


def _commodity_display(level: str) -> str:
    return f"HTS{level} & DESCRIPTION"


def build_payload(
    *,
    flow: TradeFlow,
    measure: Measure,
    year: int,
    month: int,
    commodity_level: str,
    hts_prefix: str | None = None,
) -> dict[str, object]:
    month_value = f"{month:02d}"
    commodity_column = _commodity_display(commodity_level)

    selected_commodities: list[str] = []
    selected_commodities_expanded: list[dict[str, str]] = []
    commodity_select_type = "all"
    commodities_manual = ""
    if hts_prefix:
        commodity_select_type = "list"
        selected_commodities = [hts_prefix]
        selected_commodities_expanded = [{"name": f"HTS {hts_prefix}", "value": hts_prefix}]
        commodities_manual = hts_prefix

    column_order = ["COUNTRY", commodity_column]
    full_column_order = [
        _column("Countries", "COUNTRY"),
        _column(commodity_column, commodity_column),
    ]
    sort_order = [
        {"sortData": "COUNTRY", "orderBy": "Ascending", "year": ""},
        {"sortData": commodity_column, "orderBy": "Ascending", "year": ""},
    ]

    return {
        "savedQueryType": "",
        "savedQueryID": None,
        "savedQueryName": "",
        "savedQueryDesc": "",
        "isOwner": True,
        "runMonthly": False,
        "unitConversion": "0",
        "manualConversions": [],
        "reportOptions": {
            "tradeType": flow.trade_type,
            "classificationSystem": "HTS",
        },
        "searchOptions": {
            "MiscGroup": {
                "districts": {
                    "aggregation": "Aggregate District",
                    "districtGroups": {"userGroups": []},
                    "districts": [],
                    "districtsExpanded": [],
                    "districtsSelectType": "all",
                },
                "importPrograms": {
                    "aggregation": None,
                    "importPrograms": [],
                    "programsSelectType": "all",
                },
                "extImportPrograms": {
                    "aggregation": "Aggregate CSC",
                    "extImportPrograms": [],
                    "extImportProgramsExpanded": [],
                    "programsSelectType": "all",
                },
                "provisionCodes": {
                    "aggregation": "Aggregate RPCODE",
                    "provisionCodesSelectType": "all",
                    "rateProvisionCodes": [],
                    "rateProvisionCodesExpanded": [],
                    "rateProvisionGroups": {"systemGroups": []},
                },
            },
            "commodities": {
                "aggregation": "Break Out Commodities",
                "codeDisplayFormat": "YES",
                "commodities": selected_commodities,
                "commoditiesExpanded": selected_commodities_expanded,
                "commoditiesManual": commodities_manual,
                "commodityGroups": {"systemGroups": [], "userGroups": []},
                "commoditySelectType": commodity_select_type,
                "granularity": commodity_level,
                "groupGranularity": None,
                "searchGranularity": None,
                "showHTSValidDetails": False,
            },
            "componentSettings": {
                "dataToReport": [measure.code],
                "scale": "1",
                "timeframeSelectType": "customTimePeriod",
                "years": [str(year)],
                "startDate": None,
                "endDate": None,
                "startMonth": month_value,
                "endMonth": month_value,
                "yearsTimeline": "Monthly",
            },
            "countries": {
                "aggregation": "Break Out Countries",
                "countries": [],
                "countriesExpanded": [],
                "countriesSelectType": "all",
                "countryGroups": {"systemGroups": [], "userGroups": []},
            },
        },
        "sortingAndDataFormat": {
            "DataSort": {
                "columnOrder": column_order,
                "fullColumnOrder": full_column_order,
                "sortOrder": sort_order,
            },
            "reportCustomizations": {
                "exportCombineTables": True,
                "totalRecords": "20000",
                "exportRawData": True,
            },
        },
        "deletedCountryUserGroups": [],
        "deletedCommodityUserGroups": [],
        "deletedDistrictUserGroups": [],
    }
