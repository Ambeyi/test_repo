#!/usr/bin/env python3
"""Build a Power BI dashboard project and compile a PBIT template.

This script assembles a PbixProj-compatible folder with:
- report visuals based on the devops demo report layout
- model tables/queries mapped to equipment_risk_history.csv
- risk-focused measure definitions (including critical point logic)

Then it compiles the project to a .pbit file using pbi-tools.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


WORKSPACE = Path("/workspace")
ROOT = WORKSPACE / "power_bi_dashboard"

PROJECT_DIR = ROOT / "pbix_project" / "Distribution Risk Dashboard"
OUTPUT_DIR = ROOT / "pbix"
OUTPUT_PBIT = OUTPUT_DIR / "Distribution_Risk_Dashboard.pbit"
OUTPUT_PBIX_PLACEHOLDER = OUTPUT_DIR / "Distribution_Risk_Dashboard.pbix.README.txt"

PBI_TOOLS_BIN = WORKSPACE / "tools" / "pbi-tools" / "pbi-tools.core"
DOTNET_ROOT = WORKSPACE / "tools" / "dotnet" / "runtime9"


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str) -> None:
    ensure_parent(path)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: dict | list) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def set_visual_title(config_path: Path, title: str) -> None:
    cfg = read_json(config_path)
    title_prop = (
        cfg.get("singleVisual", {})
        .get("vcObjects", {})
        .get("title", [{}])[0]
        .get("properties", {})
        .get("text")
    )
    if title_prop is None:
        return
    title_prop["expr"] = {"Literal": {"Value": f"'{title}'"}}
    write_json(config_path, cfg)


def build_project_scaffold() -> None:
    required = [
        PROJECT_DIR / "Version.txt",
        PROJECT_DIR / ".pbixproj.json",
        PROJECT_DIR / "Report",
        PROJECT_DIR / "ReportMetadata.json",
        PROJECT_DIR / "ReportSettings.json",
        PROJECT_DIR / "StaticResources",
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise RuntimeError(
            "Required project files are missing. Commit the generated project folder before running this script.\n"
            + "\n".join(missing)
        )

    # Remove stale report-level filter that references missing Date[Is Beyond Latest].
    write_json(PROJECT_DIR / "Report" / "filters.json", [])


def patch_report_metadata() -> None:
    # Page labels
    section_names = {
        "000_Sales By Category": "Risk Overview",
        "001_Models Sold": "Critical Timeline",
        "002_Commission Earned": "Geospatial Risk Impact",
        "003_Images": "Design Questions",
    }
    for folder_name, display_name in section_names.items():
        section_path = PROJECT_DIR / "Report" / "sections" / folder_name / "section.json"
        section = read_json(section_path)
        section["displayName"] = display_name
        write_json(section_path, section)

    # Key visual titles
    title_updates = {
        "Report/sections/000_Sales By Category/visualContainers/00000_Monthly Sales by Category (TEST 2)/config.json":
            "Forecast Risk Index and Critical Threshold",
        "Report/sections/000_Sales By Category/visualContainers/02000_Total Sales by Category/config.json":
            "Risk Index by Equipment Type",
        "Report/sections/000_Sales By Category/visualContainers/01000_Sales by Model and Colour/config.json":
            "Asset Risk Matrix (Asset / Region)",
        "Report/sections/001_Models Sold/visualContainers/00000_Number of Products First in March 2013/config.json":
            "Critical Assets by Equipment Type",
        "Report/sections/001_Models Sold/visualContainers/02000_Products Sold increased in April%2FJune followed by tail-off in July 2013/config.json":
            "Risk Trend with Critical Points",
        "Report/sections/001_Models Sold/visualContainers/03000_New Products in 2013 by Country and Category/config.json":
            "Critical Assets by Region and Equipment Type",
        "Report/sections/002_Commission Earned/visualContainers/00000_Commission by Reseller Location/config.json":
            "Critical Impact by Feeder / Pole Location",
        "Report/sections/002_Commission Earned/visualContainers/01000_Commission by Sales Territory/config.json":
            "Critical Impact by Region",
    }
    for rel_path, title in title_updates.items():
        set_visual_title(PROJECT_DIR / rel_path, title)


def patch_forecast_and_critical_visuals() -> None:
    # Visual 1: convert to line chart with risk and threshold lines.
    line_cfg_path = (
        PROJECT_DIR
        / "Report/sections/000_Sales By Category/visualContainers/00000_Monthly Sales by Category (TEST 2)/config.json"
    )
    cfg = read_json(line_cfg_path)
    sv = cfg["singleVisual"]
    sv["visualType"] = "lineChart"
    sv["projections"] = {
        "Category": [{"queryRef": "Date.End of Month", "active": True}],
        "Y": [
            {"queryRef": "Sales Order.Sum of Sales Amount"},
            {"queryRef": "Sales Order.Critical Threshold"},
        ],
    }
    sv["prototypeQuery"] = {
        "Version": 2,
        "From": [
            {"Name": "d", "Entity": "Date", "Type": 0},
            {"Name": "m", "Entity": "Metrics", "Type": 0},
        ],
        "Select": [
            {
                "Column": {
                    "Expression": {"SourceRef": {"Source": "d"}},
                    "Property": "End of Month",
                },
                "Name": "Date.End of Month",
            },
            {
                "Measure": {
                    "Expression": {"SourceRef": {"Source": "m"}},
                    "Property": "Sum of Sales Amount",
                },
                "Name": "Sales Order.Sum of Sales Amount",
            },
            {
                "Measure": {
                    "Expression": {"SourceRef": {"Source": "m"}},
                    "Property": "Critical Threshold",
                },
                "Name": "Sales Order.Critical Threshold",
            },
        ],
        "OrderBy": [
            {
                "Direction": 1,
                "Expression": {
                    "Column": {
                        "Expression": {"SourceRef": {"Source": "d"}},
                        "Property": "End of Month",
                    }
                },
            }
        ],
    }
    sv["columnProperties"] = {
        "Sales Order.Sum of Sales Amount": {"displayName": "Risk Index"},
        "Sales Order.Critical Threshold": {"displayName": "Critical Threshold"},
    }
    write_json(line_cfg_path, cfg)

    # Visual 2: keep combo chart and repurpose second series as critical marker.
    combo_cfg_path = (
        PROJECT_DIR
        / "Report/sections/001_Models Sold/visualContainers/02000_Products Sold increased in April%2FJune followed by tail-off in July 2013/config.json"
    )
    cfg = read_json(combo_cfg_path)
    sv = cfg["singleVisual"]
    sv["projections"] = {
        "Category": [{"queryRef": "Date.End of Month", "active": True}],
        "Y": [{"queryRef": "Sales Order.Sum of Sales Amount"}],
        "Y2": [{"queryRef": "Sales Order.Critical Point Marker"}],
    }
    sv["prototypeQuery"] = {
        "Version": 2,
        "From": [
            {"Name": "d", "Entity": "Date", "Type": 0},
            {"Name": "m", "Entity": "Metrics", "Type": 0},
        ],
        "Select": [
            {
                "Column": {
                    "Expression": {"SourceRef": {"Source": "d"}},
                    "Property": "End of Month",
                },
                "Name": "Date.End of Month",
            },
            {
                "Measure": {
                    "Expression": {"SourceRef": {"Source": "m"}},
                    "Property": "Sum of Sales Amount",
                },
                "Name": "Sales Order.Sum of Sales Amount",
            },
            {
                "Measure": {
                    "Expression": {"SourceRef": {"Source": "m"}},
                    "Property": "Critical Point Marker",
                },
                "Name": "Sales Order.Critical Point Marker",
            },
        ],
        "OrderBy": [
            {
                "Direction": 1,
                "Expression": {
                    "Column": {
                        "Expression": {"SourceRef": {"Source": "d"}},
                        "Property": "End of Month",
                    }
                },
            }
        ],
    }
    sv["columnProperties"] = {
        "Sales Order.Sum of Sales Amount": {"displayName": "Risk Index"},
        "Sales Order.Critical Point Marker": {"displayName": "Critical Point"},
    }
    write_json(combo_cfg_path, cfg)


def make_column(name: str, data_type: str, summarize_by: str = "none", **extra: object) -> dict:
    col = {
        "name": name,
        "dataType": data_type,
        "sourceColumn": name,
        "summarizeBy": summarize_by,
    }
    col.update(extra)
    return col


def build_model() -> None:
    model_dir = PROJECT_DIR / "Model"
    if model_dir.exists():
        shutil.rmtree(model_dir)

    # Database metadata and relationships.
    database = {
        "name": "Distribution Risk Dashboard",
        "compatibilityLevel": 1550,
        "model": {
            "culture": "en-US",
            "dataAccessOptions": {
                "legacyRedirects": True,
                "returnErrorValuesAsNull": True,
            },
            "defaultPowerBIDataSourceVersion": "powerBI_V3",
            "sourceQueryCulture": "en-US",
            "relationships": [
                {
                    "name": "rel_sales_product",
                    "fromTable": "Sales Order",
                    "fromColumn": "Product Number",
                    "toTable": "Product",
                    "toColumn": "Number",
                },
                {
                    "name": "rel_sales_date",
                    "fromTable": "Sales Order",
                    "fromColumn": "End of Month",
                    "toTable": "Date",
                    "toColumn": "End of Month",
                },
                {
                    "name": "rel_sales_resellers",
                    "fromTable": "Sales Order",
                    "fromColumn": "Reseller Address",
                    "toTable": "Resellers",
                    "toColumn": "Reseller Address",
                },
                {
                    "name": "rel_sales_salesperson",
                    "fromTable": "Sales Order",
                    "fromColumn": "Sales Territory Group",
                    "toTable": "Sales Person",
                    "toColumn": "Sales Territory Group",
                },
            ],
            "expressions": [
                {"name": "DataFilePath", "kind": "m"},
            ],
            "annotations": [
                {"name": "__PBI_TimeIntelligenceEnabled", "value": "0"},
                {"name": "PBIDesktopVersion", "value": "2.99.621.0 (21.11)"},
                {
                    "name": "PBI_QueryOrder",
                    "value": json.dumps(
                        [
                            "DataFilePath",
                            "RiskHistory",
                            "Date",
                            "Product",
                            "Sales Order",
                            "Resellers",
                            "Sales Person",
                            "Metrics",
                        ]
                    ),
                },
            ],
        },
    }
    write_json(model_dir / "database.json", database)

    # M queries
    write_text(
        model_dir / "queries" / "DataFilePath.m",
        "\"/workspace/power_bi_dashboard/data/equipment_risk_history.csv\"",
    )
    write_text(
        model_dir / "queries" / "RiskHistory.m",
        """let
    Source = Csv.Document(
        File.Contents(DataFilePath),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]
    ),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    ChangedType = Table.TransformColumnTypes(
        PromotedHeaders,
        {
            {"Date", type date},
            {"Region", type text},
            {"Feeder", type text},
            {"PoleNumber", type text},
            {"AssetID", type text},
            {"EquipmentType", type text},
            {"RiskIndex", type number},
            {"CriticalFlag", Int64.Type},
            {"FailureImpactUSD", Int64.Type}
        }
    )
in
    ChangedType
""",
    )
    write_text(
        model_dir / "queries" / "Date.m",
        """let
    Source = RiskHistory,
    KeepColumns = Table.SelectColumns(Source, {"Date"}),
    RenamedColumns = Table.RenameColumns(KeepColumns, {{"Date", "End of Month"}}),
    DistinctRows = Table.Distinct(RenamedColumns),
    SortedRows = Table.Sort(DistinctRows, {{"End of Month", Order.Ascending}})
in
    SortedRows
""",
    )
    write_text(
        model_dir / "queries" / "Product.m",
        """let
    Source = RiskHistory,
    KeepColumns = Table.SelectColumns(Source, {"AssetID", "EquipmentType", "Region", "Feeder"}),
    RenamedColumns = Table.RenameColumns(
        KeepColumns,
        {
            {"EquipmentType", "Category"},
            {"AssetID", "Model"},
            {"Region", "Color"},
            {"Feeder", "SubCategory"}
        }
    ),
    AddNumber = Table.AddColumn(RenamedColumns, "Number", each [Model], type text),
    AddThumbnail = Table.AddColumn(
        AddNumber,
        "Thumbnail",
        each "https://dummyimage.com/1x1/ffffff/ffffff.png",
        type text
    ),
    DistinctRows = Table.Distinct(AddThumbnail)
in
    DistinctRows
""",
    )
    write_text(
        model_dir / "queries" / "Sales Order.m",
        """let
    Source = RiskHistory,
    KeepColumns = Table.SelectColumns(
        Source,
        {"Date", "AssetID", "RiskIndex", "CriticalFlag", "FailureImpactUSD", "Region", "Feeder", "PoleNumber"}
    ),
    AddResellerAddress = Table.AddColumn(
        KeepColumns,
        "Reseller Address",
        each [Feeder] & " / " & [PoleNumber],
        type text
    ),
    RenamedColumns = Table.RenameColumns(
        AddResellerAddress,
        {
            {"Date", "End of Month"},
            {"AssetID", "Product Number"},
            {"RiskIndex", "Sales Amount"},
            {"CriticalFlag", "Sales Order Qty"},
            {"FailureImpactUSD", "Failure Impact"},
            {"Region", "Sales Territory Group"}
        }
    ),
    RemovedColumns = Table.RemoveColumns(RenamedColumns, {"Feeder", "PoleNumber"}),
    ChangedType = Table.TransformColumnTypes(
        RemovedColumns,
        {
            {"End of Month", type date},
            {"Product Number", type text},
            {"Sales Amount", type number},
            {"Sales Order Qty", Int64.Type},
            {"Failure Impact", Int64.Type},
            {"Sales Territory Group", type text},
            {"Reseller Address", type text}
        }
    )
in
    ChangedType
""",
    )
    write_text(
        model_dir / "queries" / "Resellers.m",
        """let
    Source = RiskHistory,
    KeepColumns = Table.SelectColumns(Source, {"Region", "Feeder", "PoleNumber"}),
    AddAddress = Table.AddColumn(
        KeepColumns,
        "Reseller Address",
        each [Feeder] & " / " & [PoleNumber],
        type text
    ),
    RenamedColumns = Table.RenameColumns(AddAddress, {{"Region", "Reseller Country"}}),
    RemovedColumns = Table.RemoveColumns(RenamedColumns, {"Feeder", "PoleNumber"}),
    DistinctRows = Table.Distinct(RemovedColumns)
in
    DistinctRows
""",
    )
    write_text(
        model_dir / "queries" / "Sales Person.m",
        """let
    Source = RiskHistory,
    Regions = Table.Distinct(Table.SelectColumns(Source, {"Region"})),
    RenamedColumns = Table.RenameColumns(Regions, {{"Region", "Sales Territory Group"}}),
    AddCountry = Table.AddColumn(RenamedColumns, "Sales Territory Country", each "Taiwan", type text),
    AddSalesPerson = Table.AddColumn(
        AddCountry,
        "Sales Person",
        each if [Sales Territory Group] = "North" then "North Crew"
            else if [Sales Territory Group] = "Central" then "Central Crew"
            else "South Crew",
        type text
    ),
    Reordered = Table.ReorderColumns(AddSalesPerson, {"Sales Person", "Sales Territory Country", "Sales Territory Group"})
in
    Reordered
""",
    )
    write_text(
        model_dir / "queries" / "Metrics.m",
        """let
    Source = #table(type table [Metric = text], {{"Risk KPI"}})
in
    Source
""",
    )

    # Table definitions
    write_json(model_dir / "tables" / "Date" / "table.json", {"name": "Date"})
    write_json(
        model_dir / "tables" / "Date" / "columns" / "End of Month.json",
        make_column("End of Month", "dateTime", summarize_by="none", formatString="Short Date"),
    )

    write_json(model_dir / "tables" / "Product" / "table.json", {"name": "Product"})
    product_columns = [
        make_column("Category", "string"),
        make_column("Model", "string"),
        make_column("Color", "string"),
        make_column("SubCategory", "string"),
        make_column("Number", "string"),
        make_column("Thumbnail", "string", dataCategory="ImageUrl"),
    ]
    for col in product_columns:
        write_json(model_dir / "tables" / "Product" / "columns" / f"{col['name']}.json", col)

    write_json(model_dir / "tables" / "Sales Order" / "table.json", {"name": "Sales Order"})
    sales_order_columns = [
        make_column("End of Month", "dateTime", summarize_by="none", formatString="Short Date"),
        make_column("Product Number", "string"),
        make_column("Sales Amount", "decimal", summarize_by="sum", formatString="0.0"),
        make_column("Sales Order Qty", "int64", summarize_by="sum", formatString="0"),
        make_column("Failure Impact", "int64", summarize_by="sum", formatString="0"),
        make_column("Sales Territory Group", "string"),
        make_column("Reseller Address", "string"),
    ]
    for col in sales_order_columns:
        write_json(model_dir / "tables" / "Sales Order" / "columns" / f"{col['name']}.json", col)

    write_json(model_dir / "tables" / "Resellers" / "table.json", {"name": "Resellers"})
    reseller_columns = [
        make_column("Reseller Address", "string", dataCategory="Address"),
        make_column("Reseller Country", "string", dataCategory="Country"),
    ]
    for col in reseller_columns:
        write_json(model_dir / "tables" / "Resellers" / "columns" / f"{col['name']}.json", col)
    write_json(
        model_dir / "tables" / "Resellers" / "hierarchies" / "Reseller Geography.json",
        {
            "name": "Reseller Geography",
            "levels": [
                {"name": "Reseller Country", "ordinal": 0, "column": "Reseller Country"},
                {"name": "Reseller Address", "ordinal": 1, "column": "Reseller Address"},
            ],
        },
    )

    write_json(model_dir / "tables" / "Sales Person" / "table.json", {"name": "Sales Person"})
    salesperson_columns = [
        make_column("Sales Person", "string"),
        make_column("Sales Territory Country", "string", dataCategory="Country"),
        make_column("Sales Territory Group", "string"),
    ]
    for col in salesperson_columns:
        write_json(model_dir / "tables" / "Sales Person" / "columns" / f"{col['name']}.json", col)

    write_json(model_dir / "tables" / "Metrics" / "table.json", {"name": "Metrics"})
    write_json(
        model_dir / "tables" / "Metrics" / "columns" / "Metric.json",
        make_column("Metric", "string"),
    )

    # Measures (DAX only is accepted by pbi-tools).
    metrics_measures = {
        "Sum of Sales Amount": "AVERAGE('Sales Order'[Sales Amount])",
        "Sum of Sales Order Qty": "SUM('Sales Order'[Sales Order Qty])",
        "Number of Product Sold": "DISTINCTCOUNT('Sales Order'[Product Number])",
        "Critical Threshold": """VAR Eq = SELECTEDVALUE(Product[Category])
RETURN
SWITCH(
    Eq,
    "Overhead Line", 75,
    "Insulator", 70,
    "Arrester", 72,
    72
)""",
        "Critical Point Marker": "IF([Sum of Sales Amount] >= [Critical Threshold], [Sum of Sales Amount], BLANK())",
        "Number of Products First Sold after March 2013": """CALCULATE(
    DISTINCTCOUNT('Sales Order'[Product Number]),
    FILTER(
        'Sales Order',
        'Sales Order'[Sales Amount] >= [Critical Threshold]
    )
)""",
        "_Title Sales by Category": '"Risk Index of Distribution Equipment by Type"',
        "_Title Products First Sold After March 2013": '"Critical Assets and Trend by Month"',
        "_Title Sales Commission by Geography": '"Critical Failure Impact by Region and Feeder"',
        "Action BI Toolkit": '"Design Questions"',
        "Action BI Website": '"1) Estimate failure timing/impact and response actions."',
        "Brian LinkedIn": '"2) Order actions to reduce operating cost."',
        "Mathias LinkedIn": '"3) Prioritize reliability improvements for overhead lines."',
    }
    for name, dax in metrics_measures.items():
        write_text(model_dir / "tables" / "Metrics" / "measures" / f"{name}.dax", dax + "\n")

    write_text(
        model_dir / "tables" / "Sales Person" / "measures" / "Sales Commission.dax",
        "SUM('Sales Order'[Failure Impact])\n",
    )


def validate_required_bindings() -> None:
    """Validate report query bindings against model files."""
    model_tables: dict[str, set[str]] = {}
    model_measures: dict[str, set[str]] = {}

    for table_json in (PROJECT_DIR / "Model" / "tables").glob("*/table.json"):
        table_name = json.loads(table_json.read_text(encoding="utf-8"))["name"]
        table_dir = table_json.parent
        cols = {json.loads(p.read_text(encoding="utf-8"))["name"] for p in (table_dir / "columns").glob("*.json")}
        measures = {p.stem for p in (table_dir / "measures").glob("*.dax")}
        model_tables[table_name] = cols
        model_measures[table_name] = measures

    missing_items: list[str] = []
    for config_path in (PROJECT_DIR / "Report" / "sections").rglob("config.json"):
        cfg = read_json(config_path)
        sv = cfg.get("singleVisual")
        if not sv:
            continue
        pq = sv.get("prototypeQuery", {})
        alias_to_entity = {x["Name"]: x["Entity"] for x in pq.get("From", []) if "Name" in x and "Entity" in x}
        for item in pq.get("Select", []):
            if "Column" in item:
                source_alias = item["Column"]["Expression"]["SourceRef"]["Source"]
                entity = alias_to_entity.get(source_alias)
                column = item["Column"]["Property"]
                if entity not in model_tables or column not in model_tables[entity]:
                    missing_items.append(f"{config_path}: missing column {entity}[{column}]")
            elif "Measure" in item:
                source_alias = item["Measure"]["Expression"]["SourceRef"]["Source"]
                entity = alias_to_entity.get(source_alias)
                measure = item["Measure"]["Property"]
                if entity not in model_measures or measure not in model_measures[entity]:
                    missing_items.append(f"{config_path}: missing measure {entity}[{measure}]")
            elif "HierarchyLevel" in item:
                # Hierarchy-level checks are skipped here (validated by compile step).
                continue

    if missing_items:
        joined = "\n".join(missing_items)
        raise RuntimeError(f"Report/model binding validation failed:\n{joined}")


def compile_pbit() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["DOTNET_ROOT"] = str(DOTNET_ROOT)
    env["PATH"] = f"{DOTNET_ROOT}:{env.get('PATH', '')}"
    subprocess.run(
        [
            str(PBI_TOOLS_BIN),
            "compile",
            "-folder",
            str(PROJECT_DIR),
            "-outPath",
            str(OUTPUT_PBIT),
            "-format",
            "PBIT",
            "-overwrite",
            "true",
        ],
        check=True,
        env=env,
    )

    write_text(
        OUTPUT_PBIX_PLACEHOLDER,
        """Power BI PBIX note
====================

This environment can build a model-containing template file (.pbit) using pbi-tools.
The generated file is:
  Distribution_Risk_Dashboard.pbit

To get a .pbix file:
1) Open the .pbit in Power BI Desktop.
2) Set/confirm DataFilePath (if prompted) to:
   /workspace/power_bi_dashboard/data/equipment_risk_history.csv
3) Refresh.
4) File -> Save As -> .pbix
""",
    )


def main() -> None:
    build_project_scaffold()
    patch_report_metadata()
    patch_forecast_and_critical_visuals()
    build_model()
    validate_required_bindings()
    compile_pbit()
    print(f"Generated project: {PROJECT_DIR}")
    print(f"Generated template: {OUTPUT_PBIT}")


if __name__ == "__main__":
    main()
