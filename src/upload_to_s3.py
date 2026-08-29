"""
Uploads the gold layer (business-ready summary tables) to S3, demonstrating
cross-cloud publishing of pipeline output. Also uploads the unified audit
history so downstream/cloud consumers have full lineage alongside the data.

Requires a .env file with:
  AWS_ACCESS_KEY_ID
  AWS_SECRET_ACCESS_KEY
  AWS_DEFAULT_REGION
  S3_BUCKET_NAME
"""

import os
from pathlib import Path
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
GOLD_DIR = BASE_DIR / "data" / "lakehouse" / "gold"
LAKEHOUSE_DIR = BASE_DIR / "data" / "lakehouse"

BUCKET_NAME = os.environ["S3_BUCKET_NAME"]
REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-2")

RUN_TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")

FILES_TO_UPLOAD = [
    (GOLD_DIR / "batch_quality_summary.parquet", "gold/batch_quality_summary.parquet"),
    (GOLD_DIR / "supplier_scorecard.parquet", "gold/supplier_scorecard.parquet"),
    (GOLD_DIR / "deviation_summary_by_severity.parquet", "gold/deviation_summary_by_severity.parquet"),
    (LAKEHOUSE_DIR / "unified_audit_history.parquet", "audit/unified_audit_history.parquet"),
]


def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        region_name=REGION,
    )


def upload_file(s3_client, local_path: Path, s3_key: str) -> dict:
    if not local_path.exists():
        return {"file": local_path.name, "status": "SKIPPED", "reason": "local file not found"}

    versioned_key = f"runs/{RUN_TIMESTAMP}/{s3_key}"
    latest_key = f"latest/{s3_key}"

    try:
        s3_client.upload_file(str(local_path), BUCKET_NAME, versioned_key)
        s3_client.upload_file(str(local_path), BUCKET_NAME, latest_key)
        return {
            "file": local_path.name,
            "status": "SUCCESS",
            "versioned_key": versioned_key,
            "latest_key": latest_key,
            "size_bytes": local_path.stat().st_size,
        }
    except ClientError as e:
        return {"file": local_path.name, "status": "FAILED", "reason": str(e)}


def main():
    print(f"Uploading to S3 bucket: {BUCKET_NAME} (region: {REGION})")
    print(f"Run timestamp: {RUN_TIMESTAMP}\n")

    s3_client = get_s3_client()
    results = []

    for local_path, s3_key in FILES_TO_UPLOAD:
        result = upload_file(s3_client, local_path, s3_key)
        results.append(result)
        if result["status"] == "SUCCESS":
            print(f"  {result['file']}: uploaded ({result['size_bytes']} bytes)")
            print(f"    -> s3://{BUCKET_NAME}/{result['versioned_key']}")
            print(f"    -> s3://{BUCKET_NAME}/{result['latest_key']}")
        else:
            print(f"  {result['file']}: {result['status']} - {result.get('reason', '')}")

    success_count = sum(1 for r in results if r["status"] == "SUCCESS")
    print(f"\n{success_count}/{len(FILES_TO_UPLOAD)} files uploaded successfully.")


if __name__ == "__main__":
    main()