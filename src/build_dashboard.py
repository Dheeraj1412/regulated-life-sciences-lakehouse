from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

BASE_DIR = Path(__file__).resolve().parents[1]
LAKEHOUSE_DIR = BASE_DIR / "data" / "lakehouse"
OUTPUT_PATH = BASE_DIR / "docs" / "dashboard.html"


def load_gold():
    batch_summary = pd.read_parquet(LAKEHOUSE_DIR / "gold" / "batch_quality_summary.parquet")
    supplier_scorecard = pd.read_parquet(LAKEHOUSE_DIR / "gold" / "supplier_scorecard.parquet")
    deviation_summary = pd.read_parquet(LAKEHOUSE_DIR / "gold" / "deviation_summary_by_severity.parquet")
    return batch_summary, supplier_scorecard, deviation_summary


def load_reconciliation():
    tables = ["batches", "lab_tests", "device_events", "quality_deviations",
              "supplier_inspections", "document_metadata"]
    rows = []
    for t in tables:
        bronze = len(pd.read_parquet(LAKEHOUSE_DIR / "bronze" / f"{t}.parquet"))
        silver = len(pd.read_parquet(LAKEHOUSE_DIR / "silver" / f"{t}.parquet"))
        q_path = LAKEHOUSE_DIR / "quarantine" / f"{t}.parquet"
        quarantine = len(pd.read_parquet(q_path)) if q_path.exists() else 0
        rows.append({"table": t, "silver": silver, "quarantine": quarantine})
    return pd.DataFrame(rows)


def build_dashboard():
    batch_summary, supplier_scorecard, deviation_summary = load_gold()
    reconciliation = load_reconciliation()

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "Batch Pass Rate Distribution",
            "Supplier Scorecard: Pass Rate by Supplier",
            "Open Deviations by Severity",
            "Pipeline Reconciliation: Passed vs Quarantined",
        ),
        specs=[[{"type": "histogram"}, {"type": "bar"}],
               [{"type": "bar"}, {"type": "bar"}]],
    )

    fig.add_trace(
        go.Histogram(x=batch_summary["pass_rate_pct"], nbinsx=10, marker_color="#6366f1"),
        row=1, col=1,
    )

    fig.add_trace(
        go.Bar(
            x=supplier_scorecard["supplier_name"],
            y=supplier_scorecard["pass_rate_pct"],
            marker_color="#ec4899",
        ),
        row=1, col=2,
    )

    open_deviations = deviation_summary[deviation_summary["status"] != "CLOSED"]
    severity_totals = open_deviations.groupby("severity")["count"].sum().reindex(
        ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    ).fillna(0)
    fig.add_trace(
        go.Bar(
            x=severity_totals.index,
            y=severity_totals.values,
            marker_color=["#34d399", "#fbbf24", "#fb7185", "#f43f5e"],
        ),
        row=2, col=1,
    )

    fig.add_trace(
        go.Bar(name="Passed", x=reconciliation["table"], y=reconciliation["silver"], marker_color="#6366f1"),
        row=2, col=2,
    )
    fig.add_trace(
        go.Bar(name="Quarantined", x=reconciliation["table"], y=reconciliation["quarantine"], marker_color="#fb7185"),
        row=2, col=2,
    )

    fig.update_layout(
        height=800,
        width=1100,
        title_text="NovaMed Devices — Quality Data Platform Dashboard",
        showlegend=True,
        barmode="stack",
        paper_bgcolor="#06070d",
        plot_bgcolor="#10121c",
        font=dict(color="#f2f3f9", family="Inter, sans-serif"),
        title_font=dict(size=20, color="#f2f3f9"),
    )
    fig.update_xaxes(gridcolor="#1f2233", zerolinecolor="#1f2233")
    fig.update_yaxes(gridcolor="#1f2233", zerolinecolor="#1f2233")
    for annotation in fig.layout.annotations:
        annotation.font.color = "#f2f3f9"

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(OUTPUT_PATH))
    print(f"Dashboard written to: {OUTPUT_PATH.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    build_dashboard()