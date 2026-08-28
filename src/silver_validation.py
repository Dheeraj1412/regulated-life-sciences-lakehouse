from pathlib import Path
from datetime import datetime, timezone
import uuid
import yaml
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
BRONZE_DIR = BASE_DIR / "data" / "lakehouse" / "bronze"
SILVER_DIR = BASE_DIR / "data" / "lakehouse" / "silver"
QUARANTINE_DIR = BASE_DIR / "data" / "lakehouse" / "quarantine"

SILVER_DIR.mkdir(parents=True, exist_ok=True)
QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_PATH = BASE_DIR / "config.yaml"
with open(CONFIG_PATH) as f:
    CONFIG = yaml.safe_load(f)

RUN_ID = str(uuid.uuid4())
RUN_STARTED_AT = datetime.now(timezone.utc).isoformat()


def is_valid_date(value) -> bool:
    if pd.isna(value):
        return False
    try:
        pd.to_datetime(value)
        return True
    except (ValueError, TypeError):
        return False


def apply_rules(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    """Apply every rule defined in config.yaml for this table and record failures."""
    rules = CONFIG["tables"][table_name].get("rules", {})
    errors = pd.Series([[] for _ in range(len(df))], index=df.index)

    for column in rules.get("not_null", []):
        mask = df[column].isna()
        errors[mask] = errors[mask].apply(lambda e: e + [f"missing {column}"])

    for column, allowed in rules.get("allowed_values", {}).items():
        mask = ~df[column].isin(allowed)
        errors[mask] = errors[mask].apply(lambda e: e + [f"invalid {column} value"])

    for column, bounds in rules.get("numeric_range", {}).items():
        mask = ~df[column].between(bounds["min"], bounds["max"])
        errors[mask] = errors[mask].apply(lambda e: e + [f"{column} out of range"])

    for column in rules.get("valid_date", []):
        mask = ~df[column].apply(is_valid_date)
        errors[mask] = errors[mask].apply(lambda e: e + [f"invalid {column}"])

    for pair in rules.get("date_after", []):
        before_col = pair["before_column"]
        after_col = pair["after_column"]
        before_valid = df[before_col].apply(is_valid_date)
        after_valid = df[after_col].apply(is_valid_date)
        both_valid = before_valid & after_valid
        bad_order = both_valid & (
            pd.to_datetime(df[after_col], errors="coerce")
            <= pd.to_datetime(df[before_col], errors="coerce")
        )
        errors[bad_order] = errors[bad_order].apply(
            lambda e: e + [f"{after_col} not after {before_col}"]
        )

    df = df.copy()
    df["_validation_errors"] = errors
    return df


def process_table(table_name: str) -> dict:
    bronze_path = BRONZE_DIR / f"{table_name}.parquet"
    df = pd.read_parquet(bronze_path)
    input_rows = len(df)

    rules = CONFIG["tables"][table_name].get("rules", {})

    duplicate_df = pd.DataFrame()
    if rules.get("no_duplicates", False):
        dedup_cols = [c for c in df.columns if c != "_ingested_at"]
        is_duplicate = df.duplicated(subset=dedup_cols, keep="first")
        duplicate_df = df[is_duplicate].copy()
        df = df[~is_duplicate].copy()

    validated = apply_rules(df, table_name)

    is_clean = validated["_validation_errors"].apply(len) == 0
    silver_df = validated[is_clean].drop(columns=["_validation_errors"])
    quarantine_df = validated[~is_clean].copy()
    quarantine_df["_validation_errors"] = quarantine_df["_validation_errors"].apply(", ".join)

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
    for table_name in CONFIG["tables"]:
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