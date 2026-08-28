# Regulated Life-Sciences Data Lakehouse Platform

A portfolio data engineering project implementing a **bronze → silver → gold medallion architecture** for a fictional medical-device manufacturer, with full data lineage, automated validation, rejected-record quarantine, and audit logging.

Built in Python/pandas, structured so the same logic ports directly to PySpark + Delta Lake for production scale (Databricks / Microsoft Fabric).

## Overview

**NovaMed Devices** is a fictional medical-device manufacturer that needs a centralized, governed analytics platform for laboratory test results, manufacturing batches, device-quality events, supplier inspections, quality deviations, and controlled-document metadata.

This project demonstrates the core engineering patterns required in regulated data environments: traceable ingestion, automated data-quality validation, quarantine of invalid records (never silent deletion), run-level audit logging, and business-ready reporting tables.

> **Disclaimer:** This project uses fully synthetic data. It is not an FDA-validated system and does not claim GxP or 21 CFR Part 11 compliance. It demonstrates data-engineering concepts relevant to regulated environments, including traceability, auditability, controlled schemas, validation, and error handling.

## Results

Every run is fully reconciled — every input row is accounted for as either **passed** or **quarantined with a documented reason**. No row is ever silently dropped.

| Table | Bronze (raw) | Silver (passed) | Quarantined | Pass Rate |
|---|---:|---:|---:|---:|
| batches | 120 | 118 | 2 | 98.3% |
| lab_tests | 701 | 696 | 5 | 99.3% |
| device_events | 501 | 497 | 4 | 99.2% |
| quality_deviations | 180 | 178 | 2 | 98.9% |
| supplier_inspections | 250 | 248 | 2 | 99.2% |
| document_metadata | 100 | 98 | 2 | 98.0% |
| **Total** | **1,852** | **1,835** | **17** | **99.1%** |

**Gold layer output:**
- `batch_quality_summary` — 118 batches enriched with test pass rates and open deviation counts
- `supplier_scorecard` — 5 suppliers scored on inspection pass rate and defect totals
- `deviation_summary_by_severity` — deviation counts broken down by severity × status

## Data Quality Rules

| Table | Rule | Example caught |
|---|---|---|
| batches | `batch_id` must not be null | 1 row with missing ID |
| batches | `expiry_date` must be after `manufacture_date` | 1 row with equal dates |
| lab_tests | `result` must be PASS / FAIL / PENDING | 1 row with `"UNKNOWN"` |
| lab_tests | `measurement_value` must be between 0–200 | 1 row at `999.99` |
| lab_tests | `test_date` must parse as a valid date | 1 row with `"not-a-date"` |
| lab_tests | exact duplicate rows quarantined, not dropped | 1 duplicate row |
| device_events | `severity` must be a known value | 1 row with `"EXTREME"` |
| device_events | `device_id` must not be null | 1 row with missing ID |
| device_events | `event_timestamp` must parse as valid | 1 row with `"invalid-timestamp"` |
| quality_deviations | `severity` must be a known value | 1 row with `"URGENT"` |
| supplier_inspections | `inspection_result` must be PASS / FAIL | 1 row with `"UNKNOWN"` |
| document_metadata | `approval_status` must be a known value | 1 row with `"SIGNED_OFF"` |

Every quarantined row is tagged with its specific failure reason(s) and preserved — never deleted — supporting full auditability.

## Architecture

cat README.md
git add README.md
git commit -m "Overhaul README: real pipeline results, quickstart, architecture diagram, data quality rules"
git push
cat README.md
git add README.md
git commit -m "Overhaul README: real pipeline results, quickstart, architecture diagram, data quality rules"
git push








