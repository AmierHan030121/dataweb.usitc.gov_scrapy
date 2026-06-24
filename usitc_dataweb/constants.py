from __future__ import annotations

from dataclasses import dataclass


SERVICE_BASE_URL = "https://datawebws.usitc.gov/dataweb/api/v2"
PRESENTATION_URL = "https://dataweb.usitc.gov"


@dataclass(frozen=True)
class Measure:
    code: str
    label: str
    title: str


@dataclass(frozen=True)
class TradeFlow:
    key: str
    trade_type: str
    file_prefix: str
    display_name: str
    default_level: str
    measures: tuple[Measure, ...]


FLOW_DEFINITIONS: dict[str, TradeFlow] = {
    "import_consumption": TradeFlow(
        key="import_consumption",
        trade_type="Import",
        file_prefix="IMP_Consumption",
        display_name="Imports: For Consumption",
        default_level="10",
        measures=(
            Measure("CONS_CUSTOMS_VALUE", "Customs", "Customs Value"),
            Measure("CONS_COST_INS_FREIGHT", "CIF", "CIF Import Value"),
            Measure("CONS_FIR_UNIT_QUANT", "Qty1", "First Unit of Quantity"),
            Measure("CONS_SEC_UNIT_QUANT", "Qty2", "Second Unit of Quantity"),
            Measure(
                "CONS_COST_INS_FREIGHT+CONS_CALC_DUTY",
                "LandedDutyPaid",
                "Landed Duty-Paid Value",
            ),
            Measure("CONS_CUSTOMS_VALUE_SUB_DUTY", "Dutiable", "Dutiable Value"),
            Measure("CONS_CALC_DUTY", "Duties", "Calculated Duties"),
            Measure("CONS_CHARGES_INS_FREIGHT", "ImportCharges", "Import Charges"),
        ),
    ),
    "import_general": TradeFlow(
        key="import_general",
        trade_type="GenImp",
        file_prefix="IMP_General",
        display_name="Imports: General",
        default_level="10",
        measures=(
            Measure("GEN_CUSTOMS_VALUE", "Customs", "General Customs Value"),
            Measure("GEN_COST_INS_FREIGHT", "CIF", "General CIF Imports Value"),
            Measure("GEN_FIR_UNIT_QUANTITY", "Qty1", "General First Unit of Quantity"),
            Measure("GEN_SEC_UNIT_QUANTITY", "Qty2", "General Second Unit of Quantity"),
            Measure("GEN_CHARGES_INS_FREIGHT", "ImportCharges", "General Import Charges"),
        ),
    ),
    "export_domestic": TradeFlow(
        key="export_domestic",
        trade_type="Export",
        file_prefix="EXP_Domestic",
        display_name="Exports: Domestic",
        default_level="10",
        measures=(
            Measure("FAS_VALUE", "FAS", "FAS Value"),
            Measure("FIRST_UNIT_QUANTITY", "Qty1", "First Unit of Quantity"),
            Measure("SECOND_UNIT_QUANTITY", "Qty2", "Second Unit of Quantity"),
        ),
    ),
    "export_foreign": TradeFlow(
        key="export_foreign",
        trade_type="ForeignExp",
        file_prefix="EXP_Foreign",
        display_name="Exports: Foreign",
        default_level="10",
        measures=(
            Measure("FAS_VALUE", "FAS", "FAS Value"),
            Measure("FIRST_UNIT_QUANTITY", "Qty1", "First Unit of Quantity"),
            Measure("SECOND_UNIT_QUANTITY", "Qty2", "Second Unit of Quantity"),
        ),
    ),
    "export_total": TradeFlow(
        key="export_total",
        trade_type="TotExp",
        file_prefix="EXP_Total",
        display_name="Exports: Total",
        default_level="10",
        measures=(
            Measure("FAS_VALUE", "FAS", "Total FAS Value"),
            Measure("FIRST_UNIT_QUANTITY", "Qty1", "Total First Unit of Quantity"),
            Measure("SECOND_UNIT_QUANTITY", "Qty2", "Total Second Unit of Quantity"),
        ),
    ),
    "trade_balance": TradeFlow(
        key="trade_balance",
        trade_type="Balance",
        file_prefix="BAL_TradeBalance",
        display_name="Trade Balance",
        default_level="10",
        measures=(
            Measure(
                "FAS_VALUE-GEN_CUSTOMS_VALUE",
                "FASMinusGenCustoms",
                "Total Exports FAS - General Imports Customs Val.",
            ),
        ),
    ),
}


DEFAULT_HTS2_CHAPTERS = tuple(f"{i:02d}" for i in range(1, 100))
