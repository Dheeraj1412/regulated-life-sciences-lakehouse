from pathlib import Path
from datetime import date, datetime, timedelta
import random
import uuid

import numpy as np
import pandas as pd
from faker import Faker

random.seed(42)
np.random.seed(42)
fake = Faker()
Faker.seed(42)

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / "data" / "source"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

today = date.today()
products = [
    ("PRD-100", "Cardio Monitor X1"),
    ("PRD-200", "Infusion Pump A2"),
    ("PRD-300", "Diagnostic Sensor S3"),
    ("PRD-400", "Respiratory Controller R4"),
]

suppliers = [
    ("SUP-001", "Apex Materials Inc.", "USA", "APPROVED"),
    ("SUP-002", "MedTech Components Ltd.", "Germany", "APPROVED"),
    ("SUP-003", "Precision Polymers Co.", "Japan", "APPROVED"),
    ("SUP-004", "Global BioParts LLC", "India", "CONDITIONAL"),
    ("SUP-005", "NorthStar Electronics", "Canada", "APPROVED"),
]

def random_date(start_date, end_date):
    delta_days = (end_date - start_date).days
    return start_date + timedelta(days=random.randint(0, delta_days))

def make_batches(n=120):
    rows = []

    for i in range(1, n + 1):
        product_id, product_name = random.choice(products)
        manufacture_date = random_date(today - timedelta(days=540), today - timedelta(days=20))
        expiry_date = manufacture_date + timedelta(days=random.choice([365, 540, 730]))
        batch_status = random.choices(
            ["RELEASED", "PENDING_REVIEW", "ON_HOLD", "REJECTED"],
            weights=[60, 20, 12, 8],
            k=1
        )[0]

        rows.append({
            "batch_id": f"BAT-{i:05d}",
            "product_id": product_id,
            "product_name": product_name,
            "manufacture_date": manufacture_date.isoformat(),
            "expiry_date": expiry_date.isoformat(),
            "batch_status": batch_status,
            "plant_code": random.choice(["PLANT-US-01", "PLANT-DE-01", "PLANT-CA-01"])
        })

    df = pd.DataFrame(rows)

    df.loc[3, "expiry_date"] = df.loc[3, "manufacture_date"]
    df.loc[7, "batch_id"] = None

    return df

def make_lab_tests(batches_df, n=700):
    rows = []

    valid_batch_ids = batches_df["batch_id"].dropna().tolist()

    for i in range(1, n + 1):
        batch_id = random.choice(valid_batch_ids)
        batch_row = batches_df[batches_df["batch_id"] == batch_id].iloc[0]
        manufacture_date = datetime.strptime(
            batch_row["manufacture_date"], "%Y-%m-%d"
        ).date()

        test_date = random_date(manufacture_date, min(today, manufacture_date + timedelta(days=90)))
        test_type = random.choice([
            "STERILITY",
            "BIOBURDEN",
            "VISUAL_INSPECTION",
            "FUNCTIONAL_TEST",
            "DIMENSIONAL_TEST"
        ])

        result = random.choices(
            ["PASS", "FAIL", "PENDING"],
            weights=[82, 10, 8],
            k=1
        )[0]

        rows.append({
            "test_id": f"TST-{i:06d}",
            "batch_id": batch_id,
            "device_id": f"DEV-{random.randint(1, 220):05d}",
            "test_type": test_type,
            "result": result,
            "measurement_value": round(random.uniform(88.0, 112.0), 2),
            "test_date": test_date.isoformat(),
            "laboratory_code": random.choice(["LAB-US-01", "LAB-DE-01", "LAB-CA-01"])
        })

    df = pd.DataFrame(rows)

    df.loc[5, "result"] = "UNKNOWN"
    df.loc[12, "batch_id"] = None
    df.loc[20, "measurement_value"] = 999.99
    df.loc[25, "test_date"] = "not-a-date"
    df = pd.concat([df, df.iloc[[30]]], ignore_index=True)

    return df

def make_device_events(batches_df, n=500):
    rows = []
    valid_batch_ids = batches_df["batch_id"].dropna().tolist()

    for i in range(1, n + 1):
        event_time = datetime.now() - timedelta(
            days=random.randint(0, 180),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )

        rows.append({
            "event_id": str(uuid.uuid4()),
            "device_id": f"DEV-{random.randint(1, 220):05d}",
            "batch_id": random.choice(valid_batch_ids),
            "event_type": random.choice([
                "TEMPERATURE_ALERT",
                "CALIBRATION_DUE",
                "POWER_FAILURE",
                "SENSOR_WARNING",
                "CONNECTIVITY_LOSS"
            ]),
            "severity": random.choices(
                ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
                weights=[45, 30, 18, 7],
                k=1
            )[0],
            "event_timestamp": event_time.isoformat(),
            "event_status": random.choice(["OPEN", "ACKNOWLEDGED", "RESOLVED"])
        })

    df = pd.DataFrame(rows)

    df.loc[2, "severity"] = "EXTREME"
    df.loc[9, "device_id"] = None
    df.loc[18, "event_timestamp"] = "invalid-timestamp"
    df = pd.concat([df, df.iloc[[40]]], ignore_index=True)

    return df

def make_quality_deviations(batches_df, n=180):
    rows = []
    valid_batch_ids = batches_df["batch_id"].dropna().tolist()

    for i in range(1, n + 1):
        opened_date = random_date(today - timedelta(days=365), today)
        status = random.choices(
            ["OPEN", "UNDER_INVESTIGATION", "CLOSED"],
            weights=[30, 30, 40],
            k=1
        )[0]

        closed_date = None
        if status == "CLOSED":
            closed_date = opened_date + timedelta(days=random.randint(1, 60))

        rows.append({
            "deviation_id": f"DEVN-{i:05d}",
            "batch_id": random.choice(valid_batch_ids),
            "opened_date": opened_date.isoformat(),
            "closed_date": closed_date.isoformat() if closed_date else None,
            "severity": random.choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
            "status": status,
            "description": fake.sentence(nb_words=10)
        })

    df = pd.DataFrame(rows)

    df.loc[4, "severity"] = "URGENT"
    df.loc[11, "batch_id"] = None

    return df

def make_supplier_inspections(n=250):
    rows = []

    for i in range(1, n + 1):
        supplier_id, supplier_name, country, approved_status = random.choice(suppliers)
        inspection_date = random_date(today - timedelta(days=365), today)

        rows.append({
            "inspection_id": f"INSP-{i:06d}",
            "supplier_id": supplier_id,
            "supplier_name": supplier_name,
            "country": country,
            "supplier_approval_status": approved_status,
            "material_lot": f"MAT-{random.randint(1, 500):06d}",
            "inspection_date": inspection_date.isoformat(),
            "inspection_result": random.choices(
                ["PASS", "FAIL"],
                weights=[88, 12],
                k=1
            )[0],
            "defect_count": random.randint(0, 8)
        })

    df = pd.DataFrame(rows)

    df.loc[8, "inspection_result"] = "UNKNOWN"
    df.loc[15, "supplier_id"] = None

    return df

def make_document_metadata(n=100):
    rows = []

    for i in range(1, n + 1):
        effective_date = random_date(today - timedelta(days=730), today)
        approval_status = random.choices(
            ["APPROVED", "DRAFT", "OBSOLETE", "PENDING_APPROVAL"],
            weights=[65, 10, 10, 15],
            k=1
        )[0]

        rows.append({
            "document_id": f"DOC-{i:05d}",
            "document_type": random.choice([
                "SOP",
                "WORK_INSTRUCTION",
                "TEST_PROTOCOL",
                "CALIBRATION_CERTIFICATE",
                "QUALITY_MANUAL"
            ]),
            "document_title": f"{fake.catch_phrase()} Procedure",
            "version": f"{random.randint(1, 6)}.{random.randint(0, 9)}",
            "effective_date": effective_date.isoformat(),
            "approval_status": approval_status,
            "owner_department": random.choice([
                "QUALITY_ASSURANCE",
                "MANUFACTURING",
                "LABORATORY",
                "REGULATORY_AFFAIRS"
            ])
        })

    df = pd.DataFrame(rows)

    df.loc[6, "approval_status"] = "SIGNED_OFF"
    df.loc[16, "effective_date"] = "invalid-date"

    return df

batches = make_batches()
lab_tests = make_lab_tests(batches)
device_events = make_device_events(batches)
quality_deviations = make_quality_deviations(batches)
supplier_inspections = make_supplier_inspections()
document_metadata = make_document_metadata()

batches.to_csv(OUTPUT_DIR / "batches.csv", index=False)
lab_tests.to_csv(OUTPUT_DIR / "lab_tests.csv", index=False)
device_events.to_json(
    OUTPUT_DIR / "device_events.json",
    orient="records",
    lines=True
)
quality_deviations.to_csv(OUTPUT_DIR / "quality_deviations.csv", index=False)
supplier_inspections.to_csv(OUTPUT_DIR / "supplier_inspections.csv", index=False)
document_metadata.to_csv(OUTPUT_DIR / "document_metadata.csv", index=False)

print(f"Created source data in: {OUTPUT_DIR}")
for file_path in sorted(OUTPUT_DIR.iterdir()):
    print(f"{file_path.name}: {pd.read_json(file_path, lines=True).shape[0] if file_path.suffix == '.json' else pd.read_csv(file_path).shape[0]} rows")
