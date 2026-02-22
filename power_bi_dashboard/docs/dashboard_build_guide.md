# Dashboard Build Guide (Power BI Desktop)

## 1) Goal

Build a risk-index dashboard for distribution equipment:

- Overhead lines
- Insulators
- Arresters

And satisfy your request:

- Keep the **forecast line chart**
- Add **critical point** highlighting

---

## 2) Load data

1. Open **Power BI Desktop**.
2. Get Data -> **Text/CSV**:
   - `equipment_risk_history.csv`
   - `risk_thresholds.csv`
3. In Power Query:
   - Ensure `Date` type is **Date**
   - Ensure numeric columns are numeric (`RiskIndex`, `FailureImpactUSD`, etc.)
4. Close & Apply.

---

## 3) Model setup

Create relationship:

- `risk_thresholds[EquipmentType]` (one) -> `equipment_risk_history[EquipmentType]` (many)

Optional (recommended): create Date table by pasting the `DateTable` expression from:

- `dax/risk_dashboard_measures.dax`

Then relate:

- `DateTable[Date]` (one) -> `equipment_risk_history[Date]` (many)

Use `DateTable[Date]` on time-axis visuals.

---

## 4) Add measures

Copy/paste all measures from:

- `dax/risk_dashboard_measures.dax`

Key measures for your requirement:

- `Risk Index (Avg)`
- `Critical Threshold`
- `Critical Point Marker`
- `Critical Assets (Latest)`
- `Critical Failure Impact (Latest USD)`

---

## 5) Page layout (recommended)

## Page A: Risk Overview

### Slicers (left panel)
- EquipmentType
- Region
- Feeder
- PoleNumber
- Date (between)

### KPI cards (top row)
- `Risk Index (Latest)`
- `Critical Assets (Latest)`
- `Critical Assets (%) (Latest)`
- `Critical Failure Impact (Latest USD)`

### Visual 1: Keep Forecast Line Chart

Use a **Line chart**:

- X-Axis: `DateTable[Date]` (continuous)
- Y-Axis: `Risk Index (Avg)`
- No legend, no additional measure (important for forecast availability)

In Analytics pane:

- Add **Forecast**
  - Length: 6 months
  - Ignore last: 0
  - Confidence interval: 95%
  - Seasonality: Auto

This preserves your existing forecast behavior.

### Visual 2: Add Critical Point Timeline

Use a second **Line chart** just below/next to forecast:

- X-Axis: `DateTable[Date]`
- Y values:
  - `Risk Index (Avg)`
  - `Critical Point Marker`
  - `Critical Threshold`

Formatting:

- `Risk Index (Avg)`: blue line
- `Critical Threshold`: gray dashed line
- `Critical Point Marker`: red, marker ON, line transparency high or line OFF

Result: all dates remain visible, but only critical events are marked as red points.

### Additional visuals

- **Map**:
  - Latitude / Longitude
  - Legend: EquipmentType
  - Color saturation: `Risk Index (Avg)`
- **Table/Matrix**:
  - AssetID, EquipmentType, Region, RiskIndex, RecommendedAction, FailureImpactUSD
  - Sort by RiskIndex desc

---

## Page B: Action Prioritization

Recommended visuals:

- Clustered bar:
  - Axis: EquipmentType
  - Value: `Critical Failure Impact (Latest USD)`
- Top-N table:
  - AssetID
  - RiskIndex
  - FailureImpactUSD
  - RecommendedAction
- Trend small multiples:
  - `Risk Index (Avg)` by EquipmentType

Use conditional formatting:

- >= Emergency threshold -> dark red
- >= Critical threshold -> red
- >= Warning threshold -> amber
- else -> green

---

## 6) How this answers your design questions

1. **Estimate failure timing/impact**  
   Forecast chart + critical impact KPI quantify potential future stress and cost.
2. **Reduce costs via action order**  
   Prioritization table ranks assets by risk/impact.
3. **Improve overhead line reliability**  
   Risk trend + critical markers + feeder/pole slicers identify where to act first.

---

## 7) Practical note on "forecast + critical points"

Yes, this is okay and recommended.

Power BI forecasting can be sensitive to multi-series line charts.  
To keep forecast stable, use:

- one chart dedicated to forecast
- a second chart dedicated to critical points

This gives both capabilities without sacrificing forecast quality.
