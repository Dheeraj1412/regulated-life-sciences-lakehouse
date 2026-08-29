from pathlib import Path
from datetime import datetime, timezone
import json
import uuid
import yaml
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
SOURCE_DIR = BASE_DIR / "data" / "source"
BRONZE_DIR = BASE_DIR / "data" / "lakehouse" / "bronze"
CHECKPOINT_PATH = BASE_DIR / "data" / "lakehouse" / "bronze" / "_checkpoints.json"
BRONZE_DIR.mkdir(parents=True, exist_ok=True)

CONFIG = yaml.safe_load(open(BASE_DIR / "config.yaml"))
INGESTION_TIMESTAMP = datetime.now(timezone.utc).isoformat()

SOURCE_FILES = {
    "batches": "batches.csv",
    "lab_tests": "lab_tests.csv",
    "device_events": "device_events.json",
    "quality_deviations": "quality_deviations.csv",
    "supplier_inspections": "supplier_inspections.csv",
    "document_metadata": "document_metadata.csv",
}


def load_checkpoints() -> dict:
    if CHECKPOINT_PATH.exists():
        return json.loads(CHECKPOINT_PATH.read_text())
    return {}


def save_checkpoints(checkpoints: dict):
    CHECKPOINT_PATH.write_text(json.dumps(checkpoints, indent=2))


def read_source(filename: str) -> pd.DataFrame:
    path = SOURCE_DIR / filename
    if filename.endswith(".json"):
        return pd.read_json(path, lines=True)
    return pd.read_csv(path)


def check_schema_contract(df: pd.DataFrame, table_name: str) -> list:
    required = CONFIG["tables"][table_name]["required_columns"]
    return [c for c in required if c not in df.columns]


def ingest_incremental(table_name: str, filename: str, checkpoints: dict) -> dict:
    full_df = read_source(filename)
    total_rows_in_source = len(full_df)

    last_checkpoint = checkpoints.get(table_name, 0)
    new_rows = full_df.iloc[last_checkpoint:]

    if len(new_rows) == 0:
        return {
            "table_name": table_name,
            "status": "SKIPPED",
            "new_rows": 0,
            "total_rows_in_source": total_rows_in_source,
            "checkpoint_before": last_checkpoint,
            "checkpoint_after": last_checkpoint,
        }

    missing_columns = check_schema_contract(new_rows, table_name)
    if missing_columns:
        raise ValueError(f"{table_name}: missing required columns: {missing_columns}")

    new_rows = new_rows.copy()
    new_rows["_ingested_at"] = INGESTION_TIMESTAMP
    new_rows["_source_file"] = filename
    new_rows["_source_row_count"] = total_rows_in_source

    bronze_path = BRONZE_DIR / f"{table_name}.parquet"
    if bronze_path.exists():
        existing = pd.read_parquet(bronze_path)
        combined = pd.concat([existing, new_rows], ignore_index=True)
    else:
        combined = new_rows

    combined.to_parquet(bronze_path, index=False)

    new_checkpoint = total_rows_in_source
    return {
        "table_name": table_name,
        "status": "SUCCESS",
        "new_rows": len(new_rows),
        "total_rows_in_source": total_rows_in_source,
        "checkpoint_before": last_checkpoint,
        "checkpoint_after": new_checkpoint,
    }


def main():
    run_id = str(uuid.uuid4())
    print(f"Incremental bronze ingestion run {run_id} started at {INGESTION_TIMESTAMP}\n")

    checkpoints = load_checkpoints()
    results = []

    for table_name, filename in SOURCE_FILES.items():
        result = ingest_incremental(table_name, filename, checkpoints)
        results.append(result)
        checkpoints[table_name] = result["checkpoint_after"]

        if result["status"] == "SKIPPED":
            print(f"  {table_name}: no new rows (checkpoint at {result['checkpoint_before']})")
        else:
            print(f"  {table_name}: +{result['new_rows']} new rows "
                  f"(checkpoint {result['checkpoint_before']} -> {result['checkpoint_after']})")

    save_checkpoints(checkpoints)

    audit_df = pd.DataFrame(results)
    audit_df["run_id"] = run_id
    audit_df["run_timestamp"] = INGESTION_TIMESTAMP

    audit_log_path = BRONZE_DIR / "_incremental_audit_log.parquet"
    if audit_log_path.exists():
        existing_audit = pd.read_parquet(audit_log_path)
        audit_df = pd.concat([existing_audit, audit_df], ignore_index=True)
    audit_df.to_parquet(audit_log_path, index=False)

    print(f"\nIncremental run {run_id} complete. Checkpoints saved to {CHECKPOINT_PATH.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
