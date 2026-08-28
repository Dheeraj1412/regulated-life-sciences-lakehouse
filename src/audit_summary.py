from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
LAKEHOUSE_DIR = BASE_DIR / "data" / "lakehouse"


def load_bronze_audit():
    path = LAKEHOUSE_DIR / "bronze" / "_audit_log.parquet"
    df = pd.read_parquet(path)
    df["layer"] = "bronze"
    df = df.rename(columns={"run_started_at": "run_timestamp"})
    return df[["run_id", "layer", "table_name", "row_count", "status", "run_timestamp"]]


def load_silver_audit():
    path = LAKEHOUSE_DIR / "silver" / "_validation_audit_log.parquet"
    df = pd.read_parquet(path)
    df["layer"] = "silver"
    df["status"] = "SUCCESS"
    df = df.rename(columns={"passed_rows": "row_count", "run_completed_at": "run_timestamp"})
    return df[["run_id", "layer", "table_name", "row_count", "status", "run_timestamp"]]


def load_gold_audit():
    path = LAKEHOUSE_DIR / "gold" / "_gold_audit_log.parquet"
    df = pd.read_parquet(path)
    df["layer"] = "gold"
    return df[["run_id", "layer", "table_name", "row_count", "status", "run_timestamp"]]


def main():
    bronze = load_bronze_audit()
    silver = load_silver_audit()
    gold = load_gold_audit()

    unified = pd.concat([bronze, silver, gold], ignore_index=True)
    unified = unified.sort_values("run_timestamp")

    output_path = LAKEHOUSE_DIR / "unified_audit_history.parquet"
    unified.to_parquet(output_path, index=False)

    print(f"Unified audit history: {len(unified)} records across bronze, silver, and gold\n")
    print(unified.tail(20).to_string(index=False))
    print(f"\nSaved to: {output_path.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()