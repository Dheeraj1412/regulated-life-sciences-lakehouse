from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
SILVER_DIR = BASE_DIR / "data" / "lakehouse" / "silver"
GOLD_DIR = BASE_DIR / "data" / "lakehouse" / "gold"
GOLD_DIR.mkdir(parents=True, exist_ok=True)

RUN_TIMESTAMP = datetime.now(timezone.utc).isoformat()


def load_silver(table_name: str) -> pd.DataFrame:
    return pd.read_parquet(SILVER_DIR / f"{table_name}.parquet")


def build_batch_quality_summary():
    batches = load_silver("batches")
    lab_tests = load_silver("lab_tests")
    deviations = load_silver("quality_deviations")

    test_agg = lab_tests.groupby("batch_id").agg(
        total_tests=("test_id", "count"),
        passed_tests=("result", lambda x: (x == "PASS").sum()),
        failed_tests=("result", lambda x: (x == "FAIL").sum()),
    ).reset_index()
    test_agg["pass_rate_pct"] = (
        (test_agg["passed_tests"] / test_agg["total_tests"] * 100).round(1)
    )

    open_deviations = deviations[deviations["status"] != "CLOSED"]
    deviation_agg = open_deviations.groupby("batch_id").agg(
        open_deviation_count=("deviation_id", "count")
    ).reset_index()

    summary = batches.merge(test_agg, on="batch_id", how="left")
    summary = summary.merge(deviation_agg, on="batch_id", how="left")

    summary["total_tests"] = summary["total_tests"].fillna(0).astype(int)
    summary["passed_tests"] = summary["passed_tests"].fillna(0).astype(int)
    summary["failed_tests"] = summary["failed_tests"].fillna(0).astype(int)
    summary["pass_rate_pct"] = summary["pass_rate_pct"].fillna(0.0)
    summary["open_deviation_count"] = summary["open_deviation_count"].fillna(0).astype(int)

    output_cols = [
        "batch_id", "product_name", "batch_status", "manufacture_date",
        "expiry_date", "total_tests", "passed_tests", "failed_tests",
        "pass_rate_pct", "open_deviation_count",
    ]
    return summary[output_cols]


def build_supplier_scorecard():
    inspections = load_silver("supplier_inspections")

    scorecard = inspections.groupby(["supplier_id", "supplier_name", "country"]).agg(
        total_inspections=("inspection_id", "count"),
        passed_inspections=("inspection_result", lambda x: (x == "PASS").sum()),
        total_defects=("defect_count", "sum"),
        latest_approval_status=("supplier_approval_status", "last"),
    ).reset_index()

    scorecard["pass_rate_pct"] = (
        (scorecard["passed_inspections"] / scorecard["total_inspections"] * 100).round(1)
    )
    return scorecard


def build_deviation_summary_by_severity():
    deviations = load_silver("quality_deviations")

    summary = deviations.groupby(["severity", "status"]).size().reset_index(name="count")
    return summary


def main():
    print(f"Gold modeling run started at {RUN_TIMESTAMP}\n")

    tables = {
        "batch_quality_summary": build_batch_quality_summary,
        "supplier_scorecard": build_supplier_scorecard,
        "deviation_summary_by_severity": build_deviation_summary_by_severity,
    }

    for table_name, builder in tables.items():
        df = builder()
        output_path = GOLD_DIR / f"{table_name}.parquet"
        df.to_parquet(output_path, index=False)
        print(f"  {table_name}: {len(df)} rows -> {output_path.relative_to(BASE_DIR)}")

    print("\nGold modeling complete.")


if __name__ == "__main__":
    main()