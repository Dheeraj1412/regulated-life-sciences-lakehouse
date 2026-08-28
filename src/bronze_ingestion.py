from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
SOURCE_DIR = BASE_DIR / "data" / "source"
BRONZE_DIR = BASE_DIR / "data" / "lakehouse" / "bronze"
BRONZE_DIR.mkdir(parents=True, exist_ok=True)

INGESTION_TIMESTAMP = datetime.now(timezone.utc).isoformat()

SOURCE_FILES = {
    "batches": "batches.csv",
    "lab_tests": "lab_tests.csv",
    "device_events": "device_events.json",
    "quality_deviations": "quality_deviations.csv",
    "supplier_inspections": "supplier_inspections.csv",
    "document_metadata": "document_metadata.csv",
}

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

    df = add_ingestion_metadata(df, filename)

    output_path = BRONZE_DIR / f"{table_name}.parquet"
    df.to_parquet(output_path, index=False)

    print(f"  {table_name}: {len(df)} rows -> {output_path.relative_to(BASE_DIR)}")
    return df

def main():
    print(f"Bronze ingestion started at {INGESTION_TIMESTAMP}")
    print(f"Reading from: {SOURCE_DIR}")
    print(f"Writing to:   {BRONZE_DIR}\n")

    for table_name, filename in SOURCE_FILES.items():
        ingest_file(table_name, filename)

    print("\nBronze ingestion complete.")

if __name__ == "__main__":
    main()