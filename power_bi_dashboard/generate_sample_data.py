#!/usr/bin/env python3
"""Generate sample data for a Power BI equipment risk dashboard.

The dataset is tailored for distribution overhead lines, insulators, and arresters.
It includes monthly observations and a per-equipment critical threshold table.
"""

from __future__ import annotations

import csv
import datetime as dt
import math
import random
from pathlib import Path


SEED = 42
START_MONTH = dt.date(2024, 1, 1)
END_MONTH = dt.date(2026, 2, 1)


EQUIPMENT_PROFILES = {
    "Overhead Line": {
        "prefix": "OHL",
        "count": 24,
        "base_consequence": 78,
        "warning_threshold": 65,
        "critical_threshold": 75,
        "emergency_threshold": 88,
        "load_range_a": (120, 260),
    },
    "Insulator": {
        "prefix": "INS",
        "count": 20,
        "base_consequence": 68,
        "warning_threshold": 60,
        "critical_threshold": 70,
        "emergency_threshold": 85,
        "load_range_a": (90, 220),
    },
    "Arrester": {
        "prefix": "ARR",
        "count": 16,
        "base_consequence": 72,
        "warning_threshold": 62,
        "critical_threshold": 72,
        "emergency_threshold": 86,
        "load_range_a": (100, 240),
    },
}


REGION_CENTERS = {
    "North": (25.0780, 121.2320),
    "Central": (24.1410, 120.6720),
    "South": (22.6270, 120.3010),
}

FEEDERS = ["A LINE", "B LINE", "C LINE", "D LINE"]
POLES = [f"P{i}" for i in range(1, 7)]


def month_range(start: dt.date, end: dt.date) -> list[dt.date]:
    months: list[dt.date] = []
    current = start
    while current <= end:
        months.append(current)
        year = current.year + (current.month // 12)
        month = current.month % 12 + 1
        current = dt.date(year, month, 1)
    return months


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))


def action_from_risk(risk: float) -> str:
    if risk >= 88:
        return "Immediate dispatch (24h)"
    if risk >= 75:
        return "Corrective maintenance (7d)"
    if risk >= 65:
        return "Preventive maintenance (30d)"
    return "Routine monitoring"


def build_asset_registry(rng: random.Random) -> list[dict[str, object]]:
    assets: list[dict[str, object]] = []
    for equipment_type, profile in EQUIPMENT_PROFILES.items():
        for idx in range(1, profile["count"] + 1):
            region = rng.choice(list(REGION_CENTERS.keys()))
            feeder = rng.choice(FEEDERS)
            pole = rng.choice(POLES)
            center_lat, center_lon = REGION_CENTERS[region]
            lat = center_lat + rng.uniform(-0.07, 0.07)
            lon = center_lon + rng.uniform(-0.07, 0.07)

            assets.append(
                {
                    "AssetID": f"{profile['prefix']}-{idx:03d}",
                    "EquipmentType": equipment_type,
                    "Region": region,
                    "Feeder": feeder,
                    "PoleNumber": pole,
                    "Latitude": round(lat, 6),
                    "Longitude": round(lon, 6),
                    "BaseAgeYears": rng.uniform(3.0, 32.0),
                    "BaseConditionScore": rng.uniform(4.8, 9.4),  # 1-10, high is healthy
                    "BaseMaintenanceOverdueDays": rng.uniform(5, 110),
                    "BaseConsequence": profile["base_consequence"] + rng.uniform(-8, 8),
                    "CriticalThreshold": profile["critical_threshold"],
                    "LoadRangeA": profile["load_range_a"],
                }
            )
    return assets


def compute_monthly_record(
    asset: dict[str, object],
    month_idx: int,
    date_value: dt.date,
    rng: random.Random,
) -> dict[str, object]:
    season = math.sin((2 * math.pi * month_idx) / 12)
    demand_cycle = math.cos((2 * math.pi * month_idx) / 6)

    age_years = asset["BaseAgeYears"] + (month_idx / 12.0)

    # Condition decays over time with seasonality and random noise.
    condition_score = (
        asset["BaseConditionScore"]
        - (0.075 * month_idx)
        - (0.20 * max(season, 0))
        + rng.uniform(-0.35, 0.35)
    )
    condition_score = clamp(condition_score, 1.0, 10.0)

    load_min, load_max = asset["LoadRangeA"]
    load_mid = (load_min + load_max) / 2
    load_span = (load_max - load_min) / 2
    load_a = load_mid + (load_span * (0.65 * season + 0.35 * demand_cycle)) + rng.uniform(-8, 8)
    load_a = clamp(load_a, load_min, load_max)

    weather_stress = clamp(60 + 26 * season + rng.uniform(-8, 8), 20, 100)

    maintenance_overdue_days = asset["BaseMaintenanceOverdueDays"] + (3.5 * month_idx) + rng.uniform(-12, 12)
    maintenance_overdue_days = int(clamp(maintenance_overdue_days, 0, 220))

    age_factor = clamp((age_years / 40) * 100, 0, 100)
    condition_factor = clamp((10 - condition_score) * 10, 0, 100)
    load_factor = clamp(((load_a - load_min) / (load_max - load_min)) * 100, 0, 100)
    maintenance_factor = clamp((maintenance_overdue_days / 220) * 100, 0, 100)

    # Approximate expected failures in trailing 12 months.
    failure_tendency = (
        0.35 * age_factor + 0.35 * condition_factor + 0.15 * weather_stress + 0.15 * maintenance_factor
    ) / 100
    if failure_tendency < 0.35:
        failure_count_12m = 0 if rng.random() < 0.75 else 1
    elif failure_tendency < 0.55:
        failure_count_12m = 1 if rng.random() < 0.65 else 2
    elif failure_tendency < 0.75:
        failure_count_12m = 2 if rng.random() < 0.60 else 3
    else:
        failure_count_12m = 3 if rng.random() < 0.55 else 4

    failure_factor = clamp((failure_count_12m / 4) * 100, 0, 100)
    consequence_score = clamp(asset["BaseConsequence"] + rng.uniform(-4, 4), 35, 100)

    probability_score = (
        0.20 * age_factor
        + 0.30 * condition_factor
        + 0.18 * load_factor
        + 0.15 * weather_stress
        + 0.17 * (0.65 * failure_factor + 0.35 * maintenance_factor)
    )

    # Inject occasional high-stress events to produce practical "critical point" cases.
    if season > 0.60 and rng.random() < 0.23:
        event_shock = rng.uniform(8, 20)
    elif rng.random() < 0.03:
        event_shock = rng.uniform(5, 12)
    else:
        event_shock = 0.0

    risk_index = clamp((0.76 * probability_score) + (0.24 * consequence_score) + event_shock, 0, 100)
    risk_index = round(risk_index, 1)

    equipment_type = asset["EquipmentType"]
    critical_threshold = asset["CriticalThreshold"]
    critical_flag = 1 if risk_index >= critical_threshold else 0

    if equipment_type == "Overhead Line":
        wooden_pole_tilt_deg = round(clamp(rng.gauss(5 + (risk_index / 20), 1.3), 1.0, 15.0), 2)
        interference_m = round(clamp(rng.gauss(3.0 + (risk_index / 40), 0.35), 1.2, 6.5), 2)
        insulator_contamination_pct = ""
        arrester_leakage_current_ma = ""
    elif equipment_type == "Insulator":
        wooden_pole_tilt_deg = ""
        interference_m = round(clamp(rng.gauss(2.8 + (risk_index / 50), 0.30), 1.0, 5.8), 2)
        insulator_contamination_pct = round(clamp(rng.gauss(30 + risk_index / 2, 7), 5, 95), 1)
        arrester_leakage_current_ma = ""
    else:  # Arrester
        wooden_pole_tilt_deg = ""
        interference_m = round(clamp(rng.gauss(2.6 + (risk_index / 55), 0.28), 1.0, 5.5), 2)
        insulator_contamination_pct = ""
        arrester_leakage_current_ma = round(clamp(rng.gauss(4 + risk_index / 12, 0.9), 1.0, 18.0), 2)

    inspection_cost_usd = int(110 + (20 * failure_count_12m) + rng.uniform(0, 60))
    failure_impact_usd = int(
        (850 + (risk_index * 45) + (consequence_score * 36) + (failure_count_12m * 400)) * rng.uniform(0.92, 1.08)
    )

    return {
        "Date": date_value.isoformat(),
        "Year": date_value.year,
        "Month": date_value.strftime("%b"),
        "Region": asset["Region"],
        "Feeder": asset["Feeder"],
        "PoleNumber": asset["PoleNumber"],
        "AssetID": asset["AssetID"],
        "EquipmentType": equipment_type,
        "Latitude": asset["Latitude"],
        "Longitude": asset["Longitude"],
        "AgeYears": round(age_years, 1),
        "ConditionScore": round(condition_score, 2),
        "LoadA": round(load_a, 1),
        "WoodenPoleTiltDeg": wooden_pole_tilt_deg,
        "InterferenceM": interference_m,
        "InsulatorContaminationPct": insulator_contamination_pct,
        "ArresterLeakageCurrentmA": arrester_leakage_current_ma,
        "FailureCount12M": failure_count_12m,
        "MaintenanceOverdueDays": maintenance_overdue_days,
        "ConsequenceScore": round(consequence_score, 1),
        "RiskIndex": risk_index,
        "CriticalFlag": critical_flag,
        "InspectionCostUSD": inspection_cost_usd,
        "FailureImpactUSD": failure_impact_usd,
        "RecommendedAction": action_from_risk(risk_index),
    }


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rng = random.Random(SEED)
    months = month_range(START_MONTH, END_MONTH)
    assets = build_asset_registry(rng)

    history_rows: list[dict[str, object]] = []
    for month_idx, month_value in enumerate(months):
        for asset in assets:
            history_rows.append(compute_monthly_record(asset, month_idx, month_value, rng))

    output_dir = Path(__file__).resolve().parent / "data"
    history_path = output_dir / "equipment_risk_history.csv"
    thresholds_path = output_dir / "risk_thresholds.csv"

    history_fields = [
        "Date",
        "Year",
        "Month",
        "Region",
        "Feeder",
        "PoleNumber",
        "AssetID",
        "EquipmentType",
        "Latitude",
        "Longitude",
        "AgeYears",
        "ConditionScore",
        "LoadA",
        "WoodenPoleTiltDeg",
        "InterferenceM",
        "InsulatorContaminationPct",
        "ArresterLeakageCurrentmA",
        "FailureCount12M",
        "MaintenanceOverdueDays",
        "ConsequenceScore",
        "RiskIndex",
        "CriticalFlag",
        "InspectionCostUSD",
        "FailureImpactUSD",
        "RecommendedAction",
    ]
    write_csv(history_path, history_fields, history_rows)

    threshold_rows = []
    for equipment_type, profile in EQUIPMENT_PROFILES.items():
        threshold_rows.append(
            {
                "EquipmentType": equipment_type,
                "WarningThreshold": profile["warning_threshold"],
                "CriticalThreshold": profile["critical_threshold"],
                "EmergencyThreshold": profile["emergency_threshold"],
            }
        )
    write_csv(
        thresholds_path,
        ["EquipmentType", "WarningThreshold", "CriticalThreshold", "EmergencyThreshold"],
        threshold_rows,
    )

    print(f"Generated {len(history_rows)} rows -> {history_path}")
    print(f"Generated {len(threshold_rows)} rows -> {thresholds_path}")


if __name__ == "__main__":
    main()
