"""
Simulates the NovaMed pipeline running once a day for 14 days, with a
day-to-day defect rate signal — mostly stable, with a deliberate quality
incident spiking around day 11 — so there's real historical data to
detect trends and anomalies against. This mirrors statistical process
control (SPC), the same technique used in regulated manufacturing.

After the simulation, the original clean baseline dataset is restored
and the pipeline is rerun once more, so the repo's normal bronze/silver/
gold state and documented numbers are unaffected. Only
data/lakehouse/monitoring/ retains the simulated history.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
import random
import subprocess
import shutil
import pandas as pd
import yaml

BASE_DIR = Path(__file__).resolve().parents[1]
SOURCE_DIR = BASE_DIR / "data" / "source"
LAKEHOUSE_DIR = BASE_DIR / "data" / "lakehouse"
MONITORING_DIR = LAKEHOUSE_DIR / "monitoring"
MONITORING_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(BASE_DIR / "src"))

CONFIG = yaml.safe_load(open(BASE_DIR / "config.yaml"))
NUM_DAYS = 14
INCIDENT_DAY = 11

TABLE_FILES = {
    "batches": "batches.csv",
    "lab_tests": "lab_tests.csv",
    "device_events": "device_events.json",
    "quality_deviations": "quality_deviations.csv",
    "supplier_inspections": "supplier_inspections.csv",
    "document_metadata": "document_metadata.csv",
}


def corrupt_dataframe(df: pd.DataFrame, table_name: str, rate: float) -> pd.DataFrame:
    """Randomly violate config.yaml rules on `rate` fraction of rows."""
    rules = CONFIG["tables"][table_name].get("rules", {})
    df = df.copy()
    if len(df) == 0 or rate <= 0:
        return df

    for column, _allowed in rules.get("allowed_values", {}).items():
        idx = df.sample(frac=rate, random_state=random.randint(0, 1_000_000)).index
        df.loc[idx, column] = "INVALID_VALUE"

    for column in rules.get("not_null", []):
        idx = df.sample(frac=rate / 2, random_state=random.randint(0, 1_000_000)).index
        df.loc[idx, column] = None

    for column, bounds in rules.get("numeric_range", {}).items():
        idx = df.sample(frac=rate / 2, random_state=random.randint(0, 1_000_000)).index
        df.loc[idx, column] = bounds["max"] + 999

    return df


def write_source_files(frames: dict, rate: float):
    for table_name, filename in TABLE_FILES.items():
        df = corrupt_dataframe(frames[table_name], table_name, rate)
        path = SOURCE_DIR / filename
        if filename.endswith(".json"):
            df.to_json(path, orient="records", lines=True)
        else:
            df.to_csv(path, index=False)


def run_pipeline_step(script: str):
    subprocess.run(
        [sys.executable, f"src/{script}"],
        cwd=BASE_DIR, check=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
    )


def defect_rate_for_day(day: int) -> float:
    baseline = 0.015 + random.uniform(-0.005, 0.01)
    if day == INCIDENT_DAY:
        return 0.14
    if day == INCIDENT_DAY + 1:
        return 0.06
    return max(baseline, 0.005)


def main():
    print("Loading clean baseline dataset...")
    import generate_synthetic_data as gen
    base_frames = {
        "batches": gen.batches,
        "lab_tests": gen.lab_tests,
        "device_events": gen.device_events,
        "quality_deviations": gen.quality_deviations,
        "supplier_inspections": gen.supplier_inspections,
        "document_metadata": gen.document_metadata,
    }

    print(f"\nSimulating {NUM_DAYS} days of pipeline runs...\n")
    random.seed(7)
    for day in range(1, NUM_DAYS + 1):
        rate = defect_rate_for_day(day)
        write_source_files(base_frames, rate)
        run_pipeline_step("bronze_ingestion.py")
        run_pipeline_step("silver_validation.py")
        flag = "  <-- simulated incident" if day in (INCIDENT_DAY, INCIDENT_DAY + 1) else ""
        print(f"  Day {day:>2}: defect rate {rate:5.1%}{flag}")

    print("\nExtracting trend history from the silver audit log...")
    audit = pd.read_parquet(LAKEHOUSE_DIR / "silver" / "_validation_audit_log.parquet")
    run_ids_in_order = list(dict.fromkeys(audit["run_id"]))
    last_n_runs = run_ids_in_order[-NUM_DAYS:]

    today = datetime.now(timezone.utc).date()
    trend_rows = []
    for day_index, run_id in enumerate(last_n_runs, start=1):
        sim_date = today - timedelta(days=(NUM_DAYS - day_index))
        for _, row in audit[audit["run_id"] == run_id].iterrows():
            pass_rate = (row["passed_rows"] / row["input_rows"] * 100) if row["input_rows"] else 0
            trend_rows.append({
                "simulated_day": day_index,
                "simulated_date": sim_date.isoformat(),
                "run_id": run_id,
                "table_name": row["table_name"],
                "input_rows": row["input_rows"],
                "passed_rows": row["passed_rows"],
                "quarantined_rows": row["quarantined_rows"],
                "pass_rate_pct": round(pass_rate, 2),
            })

    trends_df = pd.DataFrame(trend_rows)
    trends_df.to_parquet(MONITORING_DIR / "quality_trends.parquet", index=False)
    print(f"Saved {len(trends_df)} trend records to data/lakehouse/monitoring/quality_trends.parquet")

    print("\nRestoring the clean baseline and rebuilding bronze/silver/gold...")
    for sub in ["bronze", "silver", "quarantine", "gold"]:
        shutil.rmtree(LAKEHOUSE_DIR / sub, ignore_errors=True)
        (LAKEHOUSE_DIR / sub).mkdir(parents=True, exist_ok=True)

    write_source_files(base_frames, rate=0)
    run_pipeline_step("bronze_ingestion.py")
    run_pipeline_step("silver_validation.py")
    run_pipeline_step("gold_modeling.py")

    print("Baseline restored. Repo state matches the documented Results table again.")


if __name__ == "__main__":
    main()