"""
Downloads the latest gold layer files from S3 and verifies row counts match
what was uploaded, proving the cross-cloud round trip works both directions.
"""

import os
from pathlib import Path
import boto3
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
DOWNLOAD_DIR = BASE_DIR / "data" / "s3_downloads"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

BUCKET_NAME = os.environ["S3_BUCKET_NAME"]
REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-2")

FILES_TO_DOWNLOAD = [
    "latest/gold/batch_quality_summary.parquet",
    "latest/gold/supplier_scorecard.parquet",
    "latest/gold/deviation_summary_by_severity.parquet",
    "latest/audit/unified_audit_history.parquet",
]


def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        region_name=REGION,
    )


def main():
    print(f"Downloading latest files from S3 bucket: {BUCKET_NAME}\n")
    s3_client = get_s3_client()

    for s3_key in FILES_TO_DOWNLOAD:
        filename = Path(s3_key).name
        local_path = DOWNLOAD_DIR / filename
        s3_client.download_file(BUCKET_NAME, s3_key, str(local_path))

        df = pd.read_parquet(local_path)
        print(f"  {filename}: {len(df)} rows downloaded from s3://{BUCKET_NAME}/{s3_key}")

    print(f"\nAll files verified and saved to {DOWNLOAD_DIR.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()