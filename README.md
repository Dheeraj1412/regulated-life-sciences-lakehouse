
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

## Architecture

Source files (CSV/JSON, synthetic) feed into a bronze layer, which stores raw data plus ingestion metadata such as timestamp, source file, and run ID. From there, validation rules split each table into a silver layer (rows that pass every rule) and a quarantine layer (rows that fail, tagged with the reason). The silver layer feeds a gold layer of business-ready aggregated tables. Audit logs record the run ID, timestamps, row counts, and pass/fail status at every stage.

## Project Structure
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
│   └── pipeline_summary.py
├── docs/
├── requirements.txt
└── README.md

## Quickstart
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

## Technology Stack

- Python, pandas
- PyArrow for Parquet storage
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
- [x] Bronze ingestion with lineage metadata and audit logging
- [x] Silver validation, quarantine, and duplicate handling
- [x] Gold business-ready summary tables
- [x] Automated test suite and CI pipeline (GitHub Actions)
- [ ] Data dictionary and architecture documentation
- [ ] Quality reporting dashboard