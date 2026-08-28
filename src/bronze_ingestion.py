from pathlib import Path
from datetime import datetime, timezone
import uuid
import yaml
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
SOURCE_DIR = BASE_DIR / "data" / "source"
BRONZE_DIR = BASE_DIR / "data" / "lakehouse" / "bronze"
BRONZE_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_PATH = BASE_DIR / "config.yaml"
with open(CONFIG_PATH) as f:
    CONFIG = yaml.safe_load(f)

INGESTION_TIMESTAMP = datetime.now(timezone.utc).isoformat()

SOURCE_FILES = {
    "batches": "batches.csv",
    "lab_tests": "lab_tests.csv",
    "device_events": "device_events.json",
    "quality_deviations": "quality_deviations.csv",
    "supplier_inspections": "supplier_inspections.csv",
    "document_metadata": "document_metadata.csv",
}


def check_schema_contract(df: pd.DataFrame, table_name: str) -> list:
    """Return a list of missing required columns, empty if the schema is satisfied."""
    required = CONFIG["tables"][table_name]["required_columns"]
    missing = [col for col in required if col not in df.columns]
    return missing


def add_ingestion_metadata(df: pd.DataFrame, source_filename: str) -> pd.DataFrame:
    """Add traceability columns required for a regulated data pipeline."""
    df = df.copy()
    df["_ingested_at"] = INGESTION_TIMESTAMP
    df["_source_file"] = source_filename
    df["_source_row_count"] = len(df)
    return df


def ingest_file(table_name: str, filename: str) -> pd.DataFrame:
    file_path = SOURCE_DIR / filename

    if filename.endswith(".json"):
        df = pd.read_json(file_path, lines=True)
    else:
        df = pd.read_csv(file_path)

    missing_columns = check_schema_contract(df, table_name)
    if missing_columns:
        raise ValueError(f"{table_name}: source file is missing required columns: {missing_columns}")

    df = add_ingestion_metadata(df, filename)

    output_path = BRONZE_DIR / f"{table_name}.parquet"
    df.to_parquet(output_path, index=False)

    print(f"  {table_name}: {len(df)} rows -> {output_path.relative_to(BASE_DIR)}")
    return df


def main():
    run_id = str(uuid.uuid4())
    run_started_at = INGESTION_TIMESTAMP
    audit_records = []

    print(f"Bronze ingestion run {run_id} started at {run_started_at}")
    print(f"Reading from: {SOURCE_DIR}")
    print(f"Writing to:   {BRONZE_DIR}\n")

    overall_status = "SUCCESS"

    for table_name, filename in SOURCE_FILES.items():
        try:
            df = ingest_file(table_name, filename)
            audit_records.append({
                "run_id": run_id,
                "table_name": table_name,
                "source_file": filename,
                "row_count": len(df),
                "status": "SUCCESS",
                "error_message": None,
            })
        except Exception as e:
            overall_status = "FAILED"
            audit_records.append({
                "run_id": run_id,
                "table_name": table_name,
                "source_file": filename,
                "row_count": 0,
                "status": "FAILED",
                "error_message": str(e),
            })
            print(f"  ERROR ingesting {table_name}: {e}")

    audit_df = pd.DataFrame(audit_records)
    audit_df["run_started_at"] = run_started_at
    audit_df["run_completed_at"] = datetime.now(timezone.utc).isoformat()
    audit_df["overall_status"] = overall_status

    audit_log_path = BRONZE_DIR / "_audit_log.parquet"

    if audit_log_path.exists():
        existing_audit = pd.read_parquet(audit_log_path)
        audit_df = pd.concat([existing_audit, audit_df], ignore_index=True)

    audit_df.to_parquet(audit_log_path, index=False)

    print(f"\nBronze ingestion run {run_id} finished with status: {overall_status}")
    print(f"Audit log updated: {audit_log_path.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()