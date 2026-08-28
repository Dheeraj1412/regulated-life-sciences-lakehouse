# Regulated Life-Sciences Data Lakehouse Platform

## Overview

NovaMed Devices is a fictional medical-device manufacturer that needs a centralized, governed analytics platform for laboratory test results, manufacturing batches, device-quality events, supplier inspections, quality deviations, and controlled-document metadata.

This personal portfolio project builds an end-to-end Microsoft Fabric Lakehouse using a bronze, silver, and gold medallion architecture. It demonstrates PySpark transformation, Delta Lake storage, data-quality validation, rejected-record quarantine, lineage metadata, audit logging, and quality reporting.

## Disclaimer

This project uses fully synthetic data. It is not an FDA-validated system and does not claim GxP or 21 CFR Part 11 compliance. It demonstrates data-engineering concepts relevant to regulated environments, including traceability, auditability, controlled schemas, validation, and error handling.

## Technology Stack

- Microsoft Fabric
- OneLake and Lakehouse
- PySpark
- Delta Lake
- SQL
- Python
- PostgreSQL
- Amazon S3
- Power BI
- Git and GitHub

## Data Sources

- Manufacturing batch records
- Laboratory test results
- Device quality events
- Quality deviations
- Supplier inspections
- Controlled-document metadata

## Planned Architecture

Source systems → Fabric Data Pipeline / Notebook → Bronze Delta → Silver Delta → Gold Delta → SQL / Power BI

## Project Status

- [x] Project architecture defined
- [x] Synthetic source-data generator created
- [ ] Bronze ingestion
- [ ] Silver validation and transformations
- [ ] Gold data model
- [ ] Audit and lineage tables
- [ ] Power BI dashboard
- [ ] AWS S3 cross-cloud ingestion
