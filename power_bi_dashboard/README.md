# Power BI Dashboard Pack: Power System Equipment Risk Index

This package helps you build a dashboard for:

- Distribution overhead lines
- Insulators
- Arresters

It is designed around your request to **keep the forecast line chart** and **add critical points**.

## Included files

- `generate_sample_data.py`  
  Creates reproducible sample data for demonstration.
- `data/equipment_risk_history.csv`  
  Monthly equipment condition and risk observations.
- `data/risk_thresholds.csv`  
  Warning/critical/emergency thresholds by equipment type.
- `dax/risk_dashboard_measures.dax`  
  Ready-to-paste DAX measures and Date table definition.
- `docs/dashboard_build_guide.md`  
  Step-by-step Power BI build instructions.

## Quick start

1. (Optional) regenerate sample data:
   ```bash
   python3 power_bi_dashboard/generate_sample_data.py
   ```
2. Open Power BI Desktop.
3. Import both CSV files from `power_bi_dashboard/data/`.
4. Follow `docs/dashboard_build_guide.md`.

## Dashboard focus

The template answers these design questions:

1. Estimate failure timing/impact and support response decisions.
2. Determine action order that reduces total cost.
3. Prioritize actions to improve overhead line reliability.

## Note on forecast + critical points

In Power BI, the forecast feature works best with a **single-line time series visual**.  
To avoid losing forecast capability, this pack uses:

- **Visual 1:** Risk forecast line (with Power BI Analytics forecast)
- **Visual 2:** Critical point timeline (markers where risk >= critical threshold)
