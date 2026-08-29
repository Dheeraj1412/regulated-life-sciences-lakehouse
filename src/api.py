from pathlib import Path
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parents[1]
SOURCE_DIR = BASE_DIR / "data" / "source"
SILVER_DIR = BASE_DIR / "data" / "lakehouse" / "silver"
GOLD_DIR = BASE_DIR / "data" / "lakehouse" / "gold"
QUARANTINE_DIR = BASE_DIR / "data" / "lakehouse" / "quarantine"
STATIC_DIR = BASE_DIR / "src" / "static"

app = FastAPI(
    title="NovaMed Quality Data API",
    description=(
        "API over the regulated life-sciences lakehouse. Read endpoints serve the "
        "silver and gold layers. Write endpoints append new records to source files, "
        "which flow through the same bronze/silver validation pipeline as any "
        "batch-loaded data the next time the pipeline runs."
    ),
    version="2.1.0",
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ---------- Response models ----------

class Batch(BaseModel):
    batch_id: str
    product_name: str
    batch_status: str
    manufacture_date: str
    expiry_date: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    pass_rate_pct: float
    open_deviation_count: int


class Supplier(BaseModel):
    supplier_id: str
    supplier_name: str
    country: str
    total_inspections: int
    passed_inspections: int
    total_defects: int
    latest_approval_status: str
    pass_rate_pct: float


class DeviationSummaryRow(BaseModel):
    severity: str
    status: str
    count: int


class QuarantineRecord(BaseModel):
    table_name: str
    reason: str
    record: dict


class PaginatedResult(BaseModel):
    total: int
    limit: int
    offset: int
    results: List[dict]


# ---------- Request models ----------

class NewDeviation(BaseModel):
    batch_id: str
    severity: str = Field(..., description="LOW, MEDIUM, HIGH, or CRITICAL")
    description: str


class DeviationStatusUpdate(BaseModel):
    status: str = Field(..., description="OPEN, UNDER_INVESTIGATION, or CLOSED")


class NewDeviceEvent(BaseModel):
    device_id: str
    batch_id: str
    event_type: str = Field(..., description="TEMPERATURE_ALERT, CALIBRATION_DUE, POWER_FAILURE, SENSOR_WARNING, or CONNECTIVITY_LOSS")
    severity: str = Field(..., description="LOW, MEDIUM, HIGH, or CRITICAL")


class BatchStatusUpdate(BaseModel):
    batch_status: str = Field(..., description="RELEASED, PENDING_REVIEW, ON_HOLD, or REJECTED")


class NewSupplierInspection(BaseModel):
    supplier_id: str
    material_lot: str
    inspection_result: str = Field(..., description="PASS or FAIL")
    defect_count: int = 0


class WriteResult(BaseModel):
    status: str
    id: str
    message: str


# ---------- Helpers ----------

def load_gold(table_name: str) -> pd.DataFrame:
    path = GOLD_DIR / f"{table_name}.parquet"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{table_name} not found. Run the pipeline first.")
    return pd.read_parquet(path)


def load_silver(table_name: str) -> pd.DataFrame:
    path = SILVER_DIR / f"{table_name}.parquet"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{table_name} not found. Run the pipeline first.")
    return pd.read_parquet(path)


def append_to_source_csv(filename: str, new_row: dict):
    path = SOURCE_DIR / filename
    df = pd.read_csv(path)
    new_df = pd.DataFrame([new_row])
    df = pd.concat([df, new_df], ignore_index=True)
    df.to_csv(path, index=False)


def paginate(df: pd.DataFrame, limit: int, offset: int) -> PaginatedResult:
    total = len(df)
    page = df.iloc[offset: offset + limit]
    return PaginatedResult(total=total, limit=limit, offset=offset, results=page.to_dict(orient="records"))


# ---------- Frontend ----------

@app.get("/", include_in_schema=False)
def root():
    return FileResponse(str(STATIC_DIR / "index.html"))


# ---------- Read endpoints: gold layer ----------

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/batches", response_model=PaginatedResult)
def list_batches(
    status: Optional[str] = None,
    min_pass_rate: Optional[float] = Query(None, ge=0, le=100),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    df = load_gold("batch_quality_summary")
    if status:
        df = df[df["batch_status"] == status]
    if min_pass_rate is not None:
        df = df[df["pass_rate_pct"] >= min_pass_rate]
    return paginate(df, limit, offset)


@app.get("/batches/{batch_id}", response_model=Batch)
def get_batch(batch_id: str):
    df = load_gold("batch_quality_summary")
    match = df[df["batch_id"] == batch_id]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
    return match.iloc[0].to_dict()


@app.get("/suppliers", response_model=List[Supplier])
def list_suppliers():
    return load_gold("supplier_scorecard").to_dict(orient="records")


@app.get("/suppliers/{supplier_id}", response_model=Supplier)
def get_supplier(supplier_id: str):
    df = load_gold("supplier_scorecard")
    match = df[df["supplier_id"] == supplier_id]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Supplier {supplier_id} not found")
    return match.iloc[0].to_dict()


@app.get("/deviations/summary", response_model=List[DeviationSummaryRow])
def deviation_summary(severity: Optional[str] = None):
    df = load_gold("deviation_summary_by_severity")
    if severity:
        df = df[df["severity"] == severity]
    return df.to_dict(orient="records")


# ---------- Read endpoints: silver layer (row-level detail) ----------

@app.get("/lab-tests", response_model=PaginatedResult)
def list_lab_tests(
    batch_id: Optional[str] = None,
    result: Optional[str] = None,
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    df = load_silver("lab_tests")
    if batch_id:
        df = df[df["batch_id"] == batch_id]
    if result:
        df = df[df["result"] == result]
    return paginate(df, limit, offset)


@app.get("/device-events", response_model=PaginatedResult)
def list_device_events(
    batch_id: Optional[str] = None,
    severity: Optional[str] = None,
    event_status: Optional[str] = None,
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    df = load_silver("device_events")
    if batch_id:
        df = df[df["batch_id"] == batch_id]
    if severity:
        df = df[df["severity"] == severity]
    if event_status:
        df = df[df["event_status"] == event_status]
    return paginate(df, limit, offset)


@app.get("/deviations", response_model=PaginatedResult)
def list_deviations(
    batch_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    df = load_silver("quality_deviations")
    if batch_id:
        df = df[df["batch_id"] == batch_id]
    if status:
        df = df[df["status"] == status]
    return paginate(df, limit, offset)


@app.get("/quarantine/{table_name}", response_model=List[QuarantineRecord])
def get_quarantined_records(table_name: str, limit: int = Query(20, ge=1, le=200)):
    path = QUARANTINE_DIR / f"{table_name}.parquet"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"No quarantine data for {table_name}")
    df = pd.read_parquet(path).head(limit)
    records = []
    for _, row in df.iterrows():
        reason = row.get("_validation_errors", "unknown")
        record = row.drop(labels=["_validation_errors"], errors="ignore").to_dict()
        records.append({"table_name": table_name, "reason": reason, "record": record})
    return records


# ---------- Write endpoints ----------

@app.post("/deviations", response_model=WriteResult, status_code=201)
def create_deviation(deviation: NewDeviation):
    existing = pd.read_csv(SOURCE_DIR / "quality_deviations.csv")
    deviation_id = f"DEVN-{len(existing) + 1:05d}"

    new_row = {
        "deviation_id": deviation_id,
        "batch_id": deviation.batch_id,
        "opened_date": datetime.now(timezone.utc).date().isoformat(),
        "closed_date": None,
        "severity": deviation.severity,
        "status": "OPEN",
        "description": deviation.description,
    }
    append_to_source_csv("quality_deviations.csv", new_row)

    return WriteResult(status="created", id=deviation_id, message="Deviation logged. Run the pipeline to reflect it in silver/gold.")


@app.patch("/deviations/{deviation_id}/status", response_model=WriteResult)
def update_deviation_status(deviation_id: str, update: DeviationStatusUpdate):
    valid = ["OPEN", "UNDER_INVESTIGATION", "CLOSED"]
    if update.status not in valid:
        raise HTTPException(status_code=422, detail=f"status must be one of {valid}")

    path = SOURCE_DIR / "quality_deviations.csv"
    df = pd.read_csv(path)
    if deviation_id not in df["deviation_id"].values:
        raise HTTPException(status_code=404, detail=f"Deviation {deviation_id} not found")

    df.loc[df["deviation_id"] == deviation_id, "status"] = update.status
    if update.status == "CLOSED":
        df.loc[df["deviation_id"] == deviation_id, "closed_date"] = datetime.now(timezone.utc).date().isoformat()
    df.to_csv(path, index=False)

    return WriteResult(status="updated", id=deviation_id, message=f"Status set to {update.status}. Run the pipeline to reflect it.")


@app.post("/device-events", response_model=WriteResult, status_code=201)
def create_device_event(event: NewDeviceEvent):
    event_id = str(uuid.uuid4())
    new_row = {
        "event_id": event_id,
        "device_id": event.device_id,
        "batch_id": event.batch_id,
        "event_type": event.event_type,
        "severity": event.severity,
        "event_timestamp": datetime.now(timezone.utc).isoformat(),
        "event_status": "OPEN",
    }
    path = SOURCE_DIR / "device_events.json"
    with open(path, "a") as f:
        f.write(pd.Series(new_row).to_json() + "\n")

    return WriteResult(status="created", id=event_id, message="Device event logged. Run the pipeline to reflect it.")


@app.patch("/batches/{batch_id}/status", response_model=WriteResult)
def update_batch_status(batch_id: str, update: BatchStatusUpdate):
    valid = ["RELEASED", "PENDING_REVIEW", "ON_HOLD", "REJECTED"]
    if update.batch_status not in valid:
        raise HTTPException(status_code=422, detail=f"batch_status must be one of {valid}")

    path = SOURCE_DIR / "batches.csv"
    df = pd.read_csv(path)
    if batch_id not in df["batch_id"].values:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")

    df.loc[df["batch_id"] == batch_id, "batch_status"] = update.batch_status
    df.to_csv(path, index=False)

    return WriteResult(status="updated", id=batch_id, message=f"Batch status set to {update.batch_status}. Run the pipeline to reflect it.")


@app.post("/supplier-inspections", response_model=WriteResult, status_code=201)
def create_supplier_inspection(inspection: NewSupplierInspection):
    suppliers_df = pd.read_csv(SOURCE_DIR / "supplier_inspections.csv")

    if inspection.supplier_id not in suppliers_df["supplier_id"].values:
        raise HTTPException(status_code=404, detail=f"Supplier {inspection.supplier_id} not found")

    supplier_row = suppliers_df[suppliers_df["supplier_id"] == inspection.supplier_id].iloc[0]
    inspection_id = f"INSP-{len(suppliers_df) + 1:06d}"

    new_row = {
        "inspection_id": inspection_id,
        "supplier_id": inspection.supplier_id,
        "supplier_name": supplier_row["supplier_name"],
        "country": supplier_row["country"],
        "supplier_approval_status": supplier_row["supplier_approval_status"],
        "material_lot": inspection.material_lot,
        "inspection_date": datetime.now(timezone.utc).date().isoformat(),
        "inspection_result": inspection.inspection_result,
        "defect_count": inspection.defect_count,
    }
    append_to_source_csv("supplier_inspections.csv", new_row)

    return WriteResult(status="created", id=inspection_id, message="Inspection logged. Run the pipeline to reflect it.")