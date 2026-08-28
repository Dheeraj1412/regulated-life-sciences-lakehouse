from pathlib import Path
import pandas as pd
import pytest

BASE_DIR = Path(__file__).resolve().parents[1]
LAKEHOUSE_DIR = BASE_DIR / "data" / "lakehouse"

TABLES = [
    "batches",
    "lab_tests",
    "device_events",
    "quality_deviations",
    "supplier_inspections",
    "document_metadata",
]

ID_COLUMNS = {
    "batches": "batch_id",
    "lab_tests": "test_id",
    "device_events": "event_id",
    "quality_deviations": "deviation_id",
    "supplier_inspections": "inspection_id",
    "document_metadata": "document_id",
}


def load(layer: str, table: str) -> pd.DataFrame:
    path = LAKEHOUSE_DIR / layer / f"{table}.parquet"
    return pd.read_parquet(path)


@pytest.mark.parametrize("table", TABLES)
def test_bronze_file_exists_and_has_rows(table):
    df = load("bronze", table)
    assert len(df) > 0, f"bronze/{table}.parquet has no rows"


@pytest.mark.parametrize("table", TABLES)
def test_no_data_loss_between_bronze_and_silver_plus_quarantine(table):
    bronze = load("bronze", table)
    silver = load("silver", table)

    quarantine_path = LAKEHOUSE_DIR / "quarantine" / f"{table}.parquet"
    quarantine_count = len(pd.read_parquet(quarantine_path)) if quarantine_path.exists() else 0

    assert len(bronze) == len(silver) + quarantine_count, (
        f"{table}: bronze={len(bronze)} does not equal "
        f"silver={len(silver)} + quarantine={quarantine_count}"
    )


@pytest.mark.parametrize("table", TABLES)
def test_silver_rows_not_also_in_quarantine_for_non_duplicate_reasons(table):
    """
    An ID may legitimately appear in both silver and quarantine only when the
    quarantined copy was rejected specifically as a duplicate (the first
    occurrence passes to silver, the extra copy is quarantined). Any overlap
    for a different reason indicates a real defect.
    """
    id_col = ID_COLUMNS[table]

    silver = load("silver", table)
    quarantine_path = LAKEHOUSE_DIR / "quarantine" / f"{table}.parquet"

    if not quarantine_path.exists():
        return

    quarantine = pd.read_parquet(quarantine_path)

    silver_ids = set(silver[id_col].dropna())

    non_duplicate_quarantine = quarantine[quarantine["_validation_errors"] != "duplicate row"]
    non_duplicate_quarantine_ids = set(non_duplicate_quarantine[id_col].dropna())

    overlap = silver_ids & non_duplicate_quarantine_ids
    assert len(overlap) == 0, (
        f"{table}: {len(overlap)} IDs appear in both silver and quarantine "
        f"for reasons other than duplication"
    )


@pytest.mark.parametrize("table", TABLES)
def test_quarantine_rows_have_a_reason(table):
    quarantine_path = LAKEHOUSE_DIR / "quarantine" / f"{table}.parquet"
    if not quarantine_path.exists():
        return

    quarantine = pd.read_parquet(quarantine_path)
    if len(quarantine) == 0:
        return

    missing_reason = quarantine["_validation_errors"].isna() | (quarantine["_validation_errors"] == "")
    assert missing_reason.sum() == 0, f"{table}: {missing_reason.sum()} quarantined rows have no reason"


@pytest.mark.parametrize("table", ["batch_quality_summary", "supplier_scorecard", "deviation_summary_by_severity"])
def test_gold_tables_have_rows(table):
    df = load("gold", table)
    assert len(df) > 0, f"gold/{table}.parquet has no rows"


def test_batch_quality_summary_row_count_matches_silver_batches():
    silver_batches = load("silver", "batches")
    gold_summary = load("gold", "batch_quality_summary")
    assert len(silver_batches) == len(gold_summary), (
        f"silver batches={len(silver_batches)} does not match "
        f"gold batch_quality_summary={len(gold_summary)}"
    )


def test_supplier_scorecard_has_one_row_per_supplier():
    silver_inspections = load("silver", "supplier_inspections")
    gold_scorecard = load("gold", "supplier_scorecard")
    distinct_suppliers = silver_inspections["supplier_id"].nunique()
    assert len(gold_scorecard) == distinct_suppliers, (
        f"expected {distinct_suppliers} suppliers in scorecard, got {len(gold_scorecard)}"
    )