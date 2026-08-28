# Regulated Life-Sciences Data Lakehouse Platform

## Overview

NovaMed Devices is a fictional medical-device manufacturer that needs a centralized, governed analytics platform for laboratory test results, manufacturing batches, device-quality events, supplier inspections, quality deviations, and controlled-document metadata.

This personal portfolio project builds an end-to-end Lakehouse using a bronze, silver, and gold medallion architecture, implemented in Python and pandas and structured to be portable to PySpark and Delta Lake for production-scale deployment. It demonstrates data-quality validation, rejected-record quarantine, lineage metadata, audit logging, and quality reporting using fully synthetic data.

## Disclaimer

This project uses fully synthetic data. It is not an FDA-validated system and does not claim GxP or 21 CFR Part 11 compliance. It demonstrates data-engineering concepts relevant to regulated environments, including traceability, auditability, controlled schemas, validation, and error handling.

## Technology Stack

- Python
- pandas
- PyArrow (Parquet storage)
- SQL
- Git and GitHub

## Data Sources

- Manufacturing batch records
- Laboratory test results
- Device quality events
- Quality deviations
- Supplier inspections
- Controlled-document metadata

## Architecture

Source systems → Python ETL scripts → Bronze Parquet (raw + lineage metadata) → Silver Parquet (validated) + Quarantine (rejected records with reasons) → Gold Parquet (business-ready summaries) → Reporting

## Project Status

- [x] Project architecture defined
- [x] Synthetic source-data generator created
- [x] Bronze ingestion
- [x] Silver validation and transformations
- [ ] Gold data model
- [ ] Audit and lineage tables
- [ ] Quality reporting / dashboard
