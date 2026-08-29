from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

BASE_DIR = Path(__file__).resolve().parents[1]
MONITORING_DIR = BASE_DIR / "data" / "lakehouse" / "monitoring"
OUTPUT_PATH = BASE_DIR / "docs" / "monitoring_dashboard.html"


def main():
    trends = pd.read_parquet(MONITORING_DIR / "quality_trends.parquet")
    alerts_path = MONITORING_DIR / "quality_alerts.parquet"
    alerts = pd.read_parquet(alerts_path) if alerts_path.exists() else pd.DataFrame()

    tables = sorted(trends["table_name"].unique())

    fig = make_subplots(
        rows=len(tables), cols=1,
        subplot_titles=[f"{t}: pass rate over {trends['simulated_day'].nunique()} simulated days" for t in tables],
        shared_xaxes=True,
        vertical_spacing=0.05,
    )

    for i, table_name in enumerate(tables, start=1):
        t = trends[trends["table_name"] == table_name].sort_values("simulated_day")
        fig.add_trace(
            go.Scatter(x=t["simulated_day"], y=t["pass_rate_pct"], mode="lines+markers",
                       name=table_name, line=dict(color="#6366f1", width=2),
                       marker=dict(color="#6366f1", size=6), showlegend=False),
            row=i, col=1,
        )
        if not alerts.empty:
            table_alerts = alerts[alerts["table_name"] == table_name]
            if len(table_alerts):
                colors = table_alerts["severity"].map({"CRITICAL": "#f43f5e", "WARNING": "#fbbf24"})
                fig.add_trace(
                    go.Scatter(
                        x=table_alerts["simulated_day"], y=table_alerts["pass_rate_pct"],
                        mode="markers", marker=dict(color=colors, size=13, symbol="x"),
                        name=f"{table_name} alerts", showlegend=False,
                    ),
                    row=i, col=1,
                )

    fig.update_layout(
        height=260 * len(tables),
        width=1100,
        title_text="NovaMed Quality Monitoring — 14-Day Simulated Trend with Anomaly Detection",
        paper_bgcolor="#06070d",
        plot_bgcolor="#10121c",
        font=dict(color="#f2f3f9", family="Inter, sans-serif"),
        title_font=dict(size=20, color="#f2f3f9"),
    )
    fig.update_xaxes(gridcolor="#1f2233", zerolinecolor="#1f2233", title_text="Simulated day", row=len(tables), col=1)
    fig.update_yaxes(gridcolor="#1f2233", zerolinecolor="#1f2233", title_text="Pass rate %")
    for annotation in fig.layout.annotations:
        annotation.font.color = "#f2f3f9"

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(OUTPUT_PATH))
    print(f"Monitoring dashboard written to: {OUTPUT_PATH.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()