# Regulated Life-Sciences Data Lakehouse Platform

![Pipeline Tests](https://github.com/Dheeraj1412/regulated-life-sciences-lakehouse/actions/workflows/tests.yml/badge.svg)

A portfolio data engineering project that implements a bronze, silver, and gold medallion architecture for a fictional medical-device manufacturer. It covers data lineage, automated validation, rejected-record quarantine, and audit logging end to end.

Built in Python and pandas, structured so the same logic could be ported to PySpark and Delta Lake for production scale on Databricks or Microsoft Fabric.

## Overview

NovaMed Devices is a fictional medical-device manufacturer that needs a centralized, governed analytics platform for laboratory test results, manufacturing batches, device-quality events, supplier inspections, quality deviations, and controlled-document metadata.

This project demonstrates the core engineering patterns required in regulated data environments: traceable ingestion, automated data-quality validation, quarantine of invalid records instead of silent deletion, run-level audit logging, and business-ready reporting tables.

> Disclaimer: This project uses fully synthetic data. It is not an FDA-validated system and does not claim GxP or 21 CFR Part 11 compliance. It demonstrates data-engineering concepts relevant to regulated environments, including traceability, auditability, controlled schemas, validation, and error handling.

## Results

Every pipeline run is fully reconciled. Each input row ends up either passed or quarantined with a documented reason, so nothing is ever silently dropped.

| Table | Bronze (raw) | Silver (passed) | Quarantined | Pass Rate |
|---|---:|---:|---:|---:|
| batches | 120 | 118 | 2 | 98.3% |
| lab_tests | 701 | 696 | 5 | 99.3% |
| device_events | 501 | 497 | 4 | 99.2% |
| quality_deviations | 180 | 178 | 2 | 98.9% |
| supplier_inspections | 250 | 248 | 2 | 99.2% |
| document_metadata | 100 | 98 | 2 | 98.0% |
| Total | 1,852 | 1,835 | 17 | 99.1% |

Gold layer output:
- batch_quality_summary: 118 batches enriched with test pass rates and open deviation counts
- supplier_scorecard: 5 suppliers scored on inspection pass rate and defect totals
- deviation_summary_by_severity: deviation counts broken down by severity and status

## Data Quality Rules

All rules are defined in `config.yaml`, not hardcoded in the pipeline scripts, so thresholds and allowed values can change without touching code.

| Table | Rule | Example caught |
|---|---|---|
| batches | batch_id must not be null | 1 row with missing ID |
| batches | expiry_date must be after manufacture_date | 1 row with equal dates |
| lab_tests | result must be PASS, FAIL, or PENDING | 1 row with "UNKNOWN" |
| lab_tests | measurement_value must be between 0 and 200 | 1 row at 999.99 |
| lab_tests | test_date must parse as a valid date | 1 row with "not-a-date" |
| lab_tests | exact duplicate rows are quarantined, not dropped | 1 duplicate row |
| device_events | severity must be a known value | 1 row with "EXTREME" |
| device_events | device_id must not be null | 1 row with missing ID |
| device_events | event_timestamp must parse as valid | 1 row with "invalid-timestamp" |
| quality_deviations | severity must be a known value | 1 row with "URGENT" |
| supplier_inspections | inspection_result must be PASS or FAIL | 1 row with "UNKNOWN" |
| document_metadata | approval_status must be a known value | 1 row with "SIGNED_OFF" |

Every quarantined row is tagged with its specific failure reason and kept, never deleted, so the pipeline stays fully auditable.

## Monitoring and Anomaly Detection

Beyond validating individual pipeline runs, the platform includes statistical process control (SPC) style monitoring, tracking pass rate over time and flagging anomalies the same way a regulated manufacturing quality system would.

A simulated 14-day pipeline history was generated (`src/simulate_history.py`) with a realistic defect-rate signal: stable at 1-2% baseline, with a deliberate quality incident injected on day 11 (14% defect rate) followed by a partial recovery on day 12 (6%). The monitor (`src/monitor.py`) computes a rolling mean and standard deviation of pass rate per table and flags any day that breaches either a hard 95% threshold or a statistical lower control limit (rolling mean minus 2 standard deviations).

Result: all six tables were correctly flagged on day 11, and five remained flagged on day 12 as the incident was still resolving, with zero false positives on the 12 clean days. See `docs/monitoring_dashboard.html` for the full trend visualization with anomalies marked.

After the simulation, the pipeline automatically restores the clean baseline dataset and rebuilds bronze/silver/gold, so the repo state and documented Results table above are unaffected by the simulation.

## Architecture

Source files (CSV/JSON, synthetic) feed into a bronze layer, which stores raw data plus ingestion metadata such as timestamp, source file, and run ID, and checks each file against a schema contract defined in config.yaml. From there, validation rules split each table into a silver layer (rows that pass every rule) and a quarantine layer (rows that fail, tagged with the reason). The silver layer feeds a gold layer of business-ready aggregated tables. Audit logs record the run ID, timestamps, row counts, and pass/fail status at every stage, and a unified audit view ties bronze, silver, and gold run history together.

## Project Structure

```
regulated-life-sciences-lakehouse/
├── data/
│   ├── source/              raw synthetic source files
│   └── lakehouse/
│       ├── bronze/          raw data plus lineage metadata
│       ├── silver/          validated data and validation audit log
│       ├── quarantine/      rejected rows with reasons
│       └── gold/            business-ready summary tables
├── src/
│   ├── generate_synthetic_data.py
│   ├── bronze_ingestion.py
│   ├── silver_validation.py
│   ├── gold_modeling.py
│   ├── audit_summary.py
│   ├── build_dashboard.py
│   └── pipeline_summary.py
├── tests/
│   └── test_pipeline.py
├── docs/
│   ├── data_dictionary.md
│   └── dashboard.html
├── .github/workflows/
│   └── tests.yml
├── config.yaml
├── requirements.txt
└── README.md
```

## Quickstart

```
git clone https://github.com/Dheeraj1412/regulated-life-sciences-lakehouse.git
cd regulated-life-sciences-lakehouse
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/generate_synthetic_data.py
python src/bronze_ingestion.py
python src/silver_validation.py
python src/gold_modeling.py
python src/pipeline_summary.py

# View the unified audit history
python src/audit_summary.py

# Build and view the dashboard
python src/build_dashboard.py
open docs/dashboard.html   # macOS; use xdg-open on Linux or start on Windows

# Run the test suite
python -m pytest tests/ -v
```

### Run with Docker (alternative to manual setup)

```
docker build -t novamed-lakehouse .
docker run --rm novamed-lakehouse
```

This runs the entire pipeline (data generation through gold layer, plus the full test suite) inside an isolated container, with no local Python setup required.

## Technology Stack

- Python, pandas
- PyArrow for Parquet storage
- PyYAML for config-driven data contracts and validation rules
- Plotly for the interactive dashboard
- pytest and GitHub Actions for automated testing and CI
- Docker
- Git and GitHub

Designed to be portable to PySpark and Delta Lake for production-scale deployment on Databricks or Microsoft Fabric.

## Data Sources

- Manufacturing batch records
- Laboratory test results
- Device quality events
- Quality deviations
- Supplier inspections
- Controlled-document metadata

## Project Status

- [x] Project architecture defined
- [x] Synthetic source-data generator created
- [x] Bronze ingestion with lineage metadata, audit logging, and schema contracts
- [x] Silver validation, quarantine, and duplicate handling
- [x] Gold business-ready summary tables
- [x] Unified audit history and data dictionary
- [x] Interactive quality reporting dashboard
- [x] Automated test suite and CI pipeline (GitHub Actions)
- [x] Config-driven data contracts and schema validation
- [x] Containerization (Docker)
- [x] REST API layer with interactive dashboard UI
- [x] Statistical process control monitoring and anomaly detection

### Stretch goals

- [ ] Incremental processing
- [ ] AWS S3 cross-cloud ingestion
