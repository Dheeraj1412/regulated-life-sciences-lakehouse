from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
LAKEHOUSE_DIR = BASE_DIR / "data" / "lakehouse"

LAYERS = ["bronze", "silver", "quarantine"]

def summarize():
    print(f"{'Table':<25}{'Bronze':>10}{'Silver':>10}{'Quarantine':>12}")
    print("-" * 57)

    tables = ["batches", "lab_tests", "device_events", "quality_deviations",
              "supplier_inspections", "document_metadata"]

    for table in tables:
        counts = {}
        for layer in LAYERS:
            path = LAKEHOUSE_DIR / layer / f"{table}.parquet"
            counts[layer] = len(pd.read_parquet(path)) if path.exists() else 0
        print(f"{table:<25}{counts['bronze']:>10}{counts['silver']:>10}{counts['quarantine']:>12}")

if __name__ == "__main__":
    summarize()