from pathlib import Path
from datetime import datetime, timezone
import uuid
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
BRONZE_DIR = BASE_DIR / "data" / "lakehouse" / "bronze"
SILVER_DIR = BASE_DIR / "data" / "lakehouse" / "silver"
QUARANTINE_DIR = BASE_DIR / "data" / "lakehouse" / "quarantine"

SILVER_DIR.mkdir(parents=True, exist_ok=True)
QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)

RUN_ID = str(uuid.uuid4())
RUN_STARTED_AT = datetime.now(timezone.utc).isoformat()


def is_valid_date(value) -> bool:
    """Return True if value can be parsed as a real date, False otherwise."""
    if pd.isna(value):
        return False
    try:
        pd.to_datetime(value)
        return True
    except (ValueError, TypeError):
        return False


def validate_batches(df: pd.DataFrame) -> pd.DataFrame:
    """Add a _validation_errors column listing every rule a row breaks."""
    errors = pd.Series([[] for _ in range(len(df))], index=df.index)

    missing_id = df["batch_id"].isna()
    errors[missing_id] = errors[missing_id].apply(lambda e: e + ["missing batch_id"])

    manu_valid = df["manufacture_date"].apply(is_valid_date)
    exp_valid = df["expiry_date"].apply(is_valid_date)
    both_valid = manu_valid & exp_valid
    bad_dates = both_valid & (
        pd.to_datetime(df["expiry_date"], errors="coerce")
        <= pd.to_datetime(df["manufacture_date"], errors="coerce")
    )
    errors[bad_dates] = errors[bad_dates].apply(lambda e: e + ["expiry_date not after manufacture_date"])

    df = df.copy()
    df["_validation_errors"] = errors
    return df


def validate_lab_tests(df: pd.DataFrame) -> pd.DataFrame:
    errors = pd.Series([[] for _ in range(len(df))], index=df.index)

    bad_result = ~df["result"].isin(["PASS", "FAIL", "PENDING"])
    errors[bad_result] = errors[bad_result].apply(lambda e: e + ["invalid result value"])

    missing_batch = df["batch_id"].isna()
    errors[missing_batch] = errors[missing_batch].apply(lambda e: e + ["missing batch_id"])

    bad_measurement = ~df["measurement_value"].between(0, 200)
    errors[bad_measurement] = errors[bad_measurement].apply(lambda e: e + ["measurement_value out of range"])

    bad_date = ~df["test_date"].apply(is_valid_date)
    errors[bad_date] = errors[bad_date].apply(lambda e: e + ["invalid test_date"])

    df = df.copy()
    df["_validation_errors"] = errors
    return df


def validate_device_events(df: pd.DataFrame) -> pd.DataFrame:
    errors = pd.Series([[] for _ in range(len(df))], index=df.index)

    bad_severity = ~df["severity"].isin(["LOW", "MEDIUM", "HIGH", "CRITICAL"])
    errors[bad_severity] = errors[bad_severity].apply(lambda e: e + ["invalid severity value"])

    missing_device = df["device_id"].isna()
    errors[missing_device] = errors[missing_device].apply(lambda e: e + ["missing device_id"])

    bad_timestamp = ~df["event_timestamp"].apply(is_valid_date)
    errors[bad_timestamp] = errors[bad_timestamp].apply(lambda e: e + ["invalid event_timestamp"])

    df = df.copy()
    df["_validation_errors"] = errors
    return df


def validate_quality_deviations(df: pd.DataFrame) -> pd.DataFrame:
    errors = pd.Series([[] for _ in range(len(df))], index=df.index)

    bad_severity = ~df["severity"].isin(["LOW", "MEDIUM", "HIGH", "CRITICAL"])
    errors[bad_severity] = errors[bad_severity].apply(lambda e: e + ["invalid severity value"])

    missing_batch = df["batch_id"].isna()
    errors[missing_batch] = errors[missing_batch].apply(lambda e: e + ["missing batch_id"])

    df = df.copy()
    df["_validation_errors"] = errors
    return df


def validate_supplier_inspections(df: pd.DataFrame) -> pd.DataFrame:
    errors = pd.Series([[] for _ in range(len(df))], index=df.index)

    bad_result = ~df["inspection_result"].isin(["PASS", "FAIL"])
    errors[bad_result] = errors[bad_result].apply(lambda e: e + ["invalid inspection_result"])

    missing_supplier = df["supplier_id"].isna()
    errors[missing_supplier] = errors[missing_supplier].apply(lambda e: e + ["missing supplier_id"])

    df = df.copy()
    df["_validation_errors"] = errors
    return df


def validate_document_metadata(df: pd.DataFrame) -> pd.DataFrame:
    errors = pd.Series([[] for _ in range(len(df))], index=df.index)

    valid_statuses = ["APPROVED", "DRAFT", "OBSOLETE", "PENDING_APPROVAL"]
    bad_status = ~df["approval_status"].isin(valid_statuses)
    errors[bad_status] = errors[bad_status].apply(lambda e: e + ["invalid approval_status"])

    bad_date = ~df["effective_date"].apply(is_valid_date)
    errors[bad_date] = errors[bad_date].apply(lambda e: e + ["invalid effective_date"])

    df = df.copy()
    df["_validation_errors"] = errors
    return df


VALIDATORS = {
    "batches": validate_batches,
    "lab_tests": validate_lab_tests,
    "device_events": validate_device_events,
    "quality_deviations": validate_quality_deviations,
    "supplier_inspections": validate_supplier_inspections,
    "document_metadata": validate_document_metadata,
}

def process_table(table_name: str) -> dict:
    bronze_path = BRONZE_DIR / f"{table_name}.parquet"
    df = pd.read_parquet(bronze_path)
    input_rows = len(df)

    # Identify exact duplicate rows (keep the first occurrence, quarantine the rest)
    dedup_cols = [c for c in df.columns if c != "_ingested_at"]
    is_duplicate = df.duplicated(subset=dedup_cols, keep="first")
    duplicate_df = df[is_duplicate].copy()
    df = df[~is_duplicate].copy()

    validator = VALIDATORS[table_name]
    validated = validator(df)

    is_clean = validated["_validation_errors"].apply(len) == 0
    silver_df = validated[is_clean].drop(columns=["_validation_errors"])
    quarantine_df = validated[~is_clean].copy()
    quarantine_df["_validation_errors"] = quarantine_df["_validation_errors"].apply(lambda e: ", ".join(e))

    if len(duplicate_df) > 0:
        duplicate_df["_validation_errors"] = "duplicate row"
        quarantine_df = pd.concat([quarantine_df, duplicate_df], ignore_index=True)

    quarantine_df["_run_id"] = RUN_ID
    quarantine_df["_quarantined_at"] = RUN_STARTED_AT

    silver_df.to_parquet(SILVER_DIR / f"{table_name}.parquet", index=False)

    quarantine_path = QUARANTINE_DIR / f"{table_name}.parquet"
    new_quarantine_count = len(quarantine_df)
    if new_quarantine_count > 0:
        if quarantine_path.exists():
            existing = pd.read_parquet(quarantine_path)
            quarantine_df = pd.concat([existing, quarantine_df], ignore_index=True)
        quarantine_df.to_parquet(quarantine_path, index=False)

    print(f"  {table_name}: {len(silver_df)} passed, {new_quarantine_count} quarantined this run (input rows: {input_rows})")

    return {
        "run_id": RUN_ID,
        "table_name": table_name,
        "input_rows": input_rows,
        "passed_rows": len(silver_df),
        "quarantined_rows": new_quarantine_count,
    }

def main():
    print(f"Silver validation run {RUN_ID} started at {RUN_STARTED_AT}\n")

    audit_records = []
    for table_name in VALIDATORS:
        result = process_table(table_name)
        audit_records.append(result)

    audit_df = pd.DataFrame(audit_records)
    audit_df["run_completed_at"] = datetime.now(timezone.utc).isoformat()

    audit_log_path = SILVER_DIR / "_validation_audit_log.parquet"
    if audit_log_path.exists():
        existing_audit = pd.read_parquet(audit_log_path)
        audit_df = pd.concat([existing_audit, audit_df], ignore_index=True)
    audit_df.to_parquet(audit_log_path, index=False)

    print(f"\nSilver validation run {RUN_ID} complete.")
    print(f"Audit log: {audit_log_path.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()