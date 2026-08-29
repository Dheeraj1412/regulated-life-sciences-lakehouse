import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone
import random
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
SOURCE_DIR = BASE_DIR / "data" / "source"


def run_incremental():
    subprocess.run([sys.executable, "src/bronze_ingestion_incremental.py"], cwd=BASE_DIR, check=True)


def append_new_lab_tests(n=15):
    path = SOURCE_DIR / "lab_tests.csv"
    df = pd.read_csv(path)
    batch_ids = df["batch_id"].dropna().unique().tolist()

    new_rows = []
    for i in range(n):
        new_rows.append({
            "test_id": f"TST-NEW-{i:04d}",
            "batch_id": random.choice(batch_ids),
            "device_id": f"DEV-{random.randint(1, 220):05d}",
            "test_type": random.choice(["STERILITY", "FUNCTIONAL_TEST", "VISUAL_INSPECTION"]),
            "result": random.choices(["PASS", "FAIL"], weights=[85, 15], k=1)[0],
            "measurement_value": round(random.uniform(88.0, 112.0), 2),
            "test_date": datetime.now(timezone.utc).date().isoformat(),
            "laboratory_code": "LAB-US-01",
        })

    new_df = pd.DataFrame(new_rows)
    combined = pd.concat([df, new_df], ignore_index=True)
    combined.to_csv(path, index=False)
    return n


def main():
    print("=" * 70)
    print("STEP 1: Establish baseline checkpoint (processes all current rows)")
    print("=" * 70)
    run_incremental()

    print("\n" + "=" * 70)
    print("STEP 2: Run again immediately -- should skip everything (no new data)")
    print("=" * 70)
    run_incremental()

    print("\n" + "=" * 70)
    print("STEP 3: Simulate new data arriving")
    print("=" * 70)
    added = append_new_lab_tests(15)
    print(f"Appended {added} new lab_tests rows to source file.")

    print("\n" + "=" * 70)
    print("STEP 4: Run incrementally -- should process ONLY the new rows")
    print("=" * 70)
    run_incremental()

    print("\n" + "=" * 70)
    print("Demo complete. Check data/lakehouse/bronze/_incremental_audit_log.parquet")
    print("for the full history of what was processed in each run.")
    print("=" * 70)


if __name__ == "__main__":
    main()
