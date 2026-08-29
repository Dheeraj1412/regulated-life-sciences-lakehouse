"""
Statistical process control style monitoring: computes a rolling mean and
standard deviation of pass rate per table, then flags any simulated day
where the pass rate breaches a hard business threshold, a statistical
control limit (rolling mean - 2 std devs), or both.
"""

from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
MONITORING_DIR = BASE_DIR / "data" / "lakehouse" / "monitoring"

HARD_THRESHOLD_PCT = 95.0
ROLLING_WINDOW = 5
STD_MULTIPLIER = 2


def main():
    trends_path = MONITORING_DIR / "quality_trends.parquet"
    if not trends_path.exists():
        print("No trend history found. Run src/simulate_history.py first.")
        return

    df = pd.read_parquet(trends_path).sort_values(["table_name", "simulated_day"])

    alerts = []
    for table_name, group in df.groupby("table_name"):
        group = group.sort_values("simulated_day").reset_index(drop=True)
        group["rolling_mean"] = group["pass_rate_pct"].rolling(ROLLING_WINDOW, min_periods=3).mean()
        group["rolling_std"] = group["pass_rate_pct"].rolling(ROLLING_WINDOW, min_periods=3).std().fillna(0)
        group["lower_control_limit"] = group["rolling_mean"] - STD_MULTIPLIER * group["rolling_std"]

        for _, row in group.iterrows():
            breaches_threshold = row["pass_rate_pct"] < HARD_THRESHOLD_PCT
            breaches_control_limit = (
                pd.notna(row["lower_control_limit"])
                and row["pass_rate_pct"] < row["lower_control_limit"]
            )

            if breaches_threshold and breaches_control_limit:
                severity = "CRITICAL"
            elif breaches_threshold or breaches_control_limit:
                severity = "WARNING"
            else:
                continue

            alerts.append({
                "simulated_day": row["simulated_day"],
                "simulated_date": row["simulated_date"],
                "table_name": table_name,
                "pass_rate_pct": row["pass_rate_pct"],
                "rolling_mean_pct": round(row["rolling_mean"], 2) if pd.notna(row["rolling_mean"]) else None,
                "lower_control_limit_pct": round(row["lower_control_limit"], 2) if pd.notna(row["lower_control_limit"]) else None,
                "severity": severity,
            })

    alerts_df = pd.DataFrame(alerts)
    alerts_df.to_parquet(MONITORING_DIR / "quality_alerts.parquet", index=False)

    print(f"Evaluated {df['table_name'].nunique()} tables across {df['simulated_day'].nunique()} simulated days.")
    print(f"Alerts raised: {len(alerts_df)}\n")
    if len(alerts_df):
        print(alerts_df[["simulated_day", "table_name", "pass_rate_pct", "lower_control_limit_pct", "severity"]].to_string(index=False))
    else:
        print("No anomalies detected.")


if __name__ == "__main__":
    main()