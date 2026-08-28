# Data Dictionary

This document defines every column across the bronze, silver, and gold layers of the pipeline. Columns prefixed with an underscore (for example `_ingested_at`) are pipeline-generated metadata and are not part of the original source data.

## Source and Bronze/Silver Tables

### batches

| Column | Type | Description |
|---|---|---|
| batch_id | string | Unique identifier for a manufacturing batch |
| product_id | string | Identifier for the product manufactured in this batch |
| product_name | string | Human-readable product name |
| manufacture_date | date | Date the batch was manufactured |
| expiry_date | date | Date the batch expires, must be after manufacture_date |
| batch_status | string | One of RELEASED, PENDING_REVIEW, ON_HOLD, REJECTED |
| plant_code | string | Facility where the batch was manufactured |
| _ingested_at | timestamp | When this row was loaded into bronze |
| _source_file | string | Originating source file name |
| _source_row_count | integer | Total row count of the source file at ingestion time |

### lab_tests

| Column | Type | Description |
|---|---|---|
| test_id | string | Unique identifier for a lab test |
| batch_id | string | Batch this test was performed on, foreign key to batches |
| device_id | string | Device associated with the test |
| test_type | string | One of STERILITY, BIOBURDEN, VISUAL_INSPECTION, FUNCTIONAL_TEST, DIMENSIONAL_TEST |
| result | string | One of PASS, FAIL, PENDING |
| measurement_value | float | Numeric test measurement, expected range 0 to 200 |
| test_date | date | Date the test was performed |
| laboratory_code | string | Laboratory that performed the test |
| _ingested_at | timestamp | When this row was loaded into bronze |
| _source_file | string | Originating source file name |
| _source_row_count | integer | Total row count of the source file at ingestion time |

### device_events

| Column | Type | Description |
|---|---|---|
| event_id | string | Unique identifier for a device event |
| device_id | string | Device that generated the event |
| batch_id | string | Batch associated with the device, foreign key to batches |
| event_type | string | One of TEMPERATURE_ALERT, CALIBRATION_DUE, POWER_FAILURE, SENSOR_WARNING, CONNECTIVITY_LOSS |
| severity | string | One of LOW, MEDIUM, HIGH, CRITICAL |
| event_timestamp | timestamp | When the event occurred |
| event_status | string | One of OPEN, ACKNOWLEDGED, RESOLVED |
| _ingested_at | timestamp | When this row was loaded into bronze |
| _source_file | string | Originating source file name |
| _source_row_count | integer | Total row count of the source file at ingestion time |

### quality_deviations

| Column | Type | Description |
|---|---|---|
| deviation_id | string | Unique identifier for a quality deviation |
| batch_id | string | Batch the deviation relates to, foreign key to batches |
| opened_date | date | Date the deviation was opened |
| closed_date | date | Date the deviation was closed, null if still open |
| severity | string | One of LOW, MEDIUM, HIGH, CRITICAL |
| status | string | One of OPEN, UNDER_INVESTIGATION, CLOSED |
| description | string | Free text description of the deviation |
| _ingested_at | timestamp | When this row was loaded into bronze |
| _source_file | string | Originating source file name |
| _source_row_count | integer | Total row count of the source file at ingestion time |

### supplier_inspections

| Column | Type | Description |
|---|---|---|
| inspection_id | string | Unique identifier for a supplier inspection |
| supplier_id | string | Identifier for the supplier |
| supplier_name | string | Name of the supplier |
| country | string | Supplier's country |
| supplier_approval_status | string | One of APPROVED, CONDITIONAL |
| material_lot | string | Lot number of the inspected material |
| inspection_date | date | Date of the inspection |
| inspection_result | string | One of PASS, FAIL |
| defect_count | integer | Number of defects found during inspection |
| _ingested_at | timestamp | When this row was loaded into bronze |
| _source_file | string | Originating source file name |
| _source_row_count | integer | Total row count of the source file at ingestion time |

### document_metadata

| Column | Type | Description |
|---|---|---|
| document_id | string | Unique identifier for a controlled document |
| document_type | string | One of SOP, WORK_INSTRUCTION, TEST_PROTOCOL, CALIBRATION_CERTIFICATE, QUALITY_MANUAL |
| document_title | string | Title of the document |
| version | string | Document version number |
| effective_date | date | Date the document became effective |
| approval_status | string | One of APPROVED, DRAFT, OBSOLETE, PENDING_APPROVAL |
| owner_department | string | One of QUALITY_ASSURANCE, MANUFACTURING, LABORATORY, REGULATORY_AFFAIRS |
| _ingested_at | timestamp | When this row was loaded into bronze |
| _source_file | string | Originating source file name |
| _source_row_count | integer | Total row count of the source file at ingestion time |

## Quarantine Tables

Each quarantine table mirrors its source table's columns, plus:

| Column | Type | Description |
|---|---|---|
| _validation_errors | string | Comma separated list of every rule this row failed |
| _run_id | string | ID of the silver validation run that quarantined this row |
| _quarantined_at | timestamp | When this row was quarantined |

## Gold Tables

### batch_quality_summary

| Column | Type | Description |
|---|---|---|
| batch_id | string | Unique identifier for the batch |
| product_name | string | Product manufactured in this batch |
| batch_status | string | Current batch status |
| manufacture_date | date | Date of manufacture |
| expiry_date | date | Date of expiry |
| total_tests | integer | Total lab tests recorded for this batch |
| passed_tests | integer | Number of tests with result PASS |
| failed_tests | integer | Number of tests with result FAIL |
| pass_rate_pct | float | Percentage of tests that passed |
| open_deviation_count | integer | Number of quality deviations still open for this batch |

### supplier_scorecard

| Column | Type | Description |
|---|---|---|
| supplier_id | string | Unique identifier for the supplier |
| supplier_name | string | Name of the supplier |
| country | string | Supplier's country |
| total_inspections | integer | Total inspections recorded |
| passed_inspections | integer | Number of inspections with result PASS |
| total_defects | integer | Sum of defect counts across all inspections |
| latest_approval_status | string | Most recent supplier approval status observed |
| pass_rate_pct | float | Percentage of inspections that passed |

### deviation_summary_by_severity

| Column | Type | Description |
|---|---|---|
| severity | string | Deviation severity level |
| status | string | Deviation status |
| count | integer | Number of deviations matching this severity and status combination |

## Audit Tables

### unified_audit_history

| Column | Type | Description |
|---|---|---|
| run_id | string | Unique identifier for a single pipeline run |
| layer | string | One of bronze, silver, gold |
| table_name | string | Table produced by this run |
| row_count | integer | Number of rows produced in this run for this table |
| status | string | SUCCESS or FAILED |
| run_timestamp | timestamp | When this run occurred |