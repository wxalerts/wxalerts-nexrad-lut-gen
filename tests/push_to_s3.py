#!/usr/bin/env python3
"""
One-shot upload of pre-generated NEXRAD LUTs to SeaweedFS S3.
Skips files that already exist in the bucket with matching size.
"""

import os
import sys
import boto3
from botocore.client import Config
from pathlib import Path

# --- Config ---
ENDPOINT     = "http://172.16.50.11:9000"
ACCESS_KEY   = "O2MZXHLFBDC6YB55CDGE"
SECRET_KEY   = "NjRuSMHhMgWEF864TmRxVB_AXi-VUzZCtzf8Jun3hEjkUITCHHsdFw"
BUCKET       = "nexrad-lut"
SOURCE_DIR   = Path("/home/cchance/Documents/GitHub/wxalerts-nexrad-lut-gen/nexrad-luts/sites")

def main():
    s3 = boto3.client(
        "s3",
        endpoint_url=ENDPOINT,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )

    # Build a map of existing objects in the bucket: key -> size
    print("Fetching existing objects from bucket...")
    existing = {}
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET):
        for obj in page.get("Contents", []):
            existing[obj["Key"]] = obj["Size"]
    print(f"  Found {len(existing)} existing objects")

    # Walk local source directory
    files = [f for f in SOURCE_DIR.rglob("*") if f.is_file()]
    print(f"  Found {len(files)} local files to check")

    uploaded = 0
    skipped  = 0
    failed   = 0

    for local_path in sorted(files):
        s3_key     = str(local_path.relative_to(SOURCE_DIR))
        local_size = local_path.stat().st_size

        if s3_key in existing and existing[s3_key] == local_size:
            skipped += 1
            continue

        try:
            s3.upload_file(str(local_path), BUCKET, s3_key)
            print(f"  uploaded: {s3_key}")
            uploaded += 1
        except Exception as e:
            print(f"  FAILED:   {s3_key} — {e}", file=sys.stderr)
            failed += 1

    print(f"\nDone. uploaded={uploaded}  skipped={skipped}  failed={failed}")
    if failed:
        sys.exit(1)

if __name__ == "__main__":
    main()