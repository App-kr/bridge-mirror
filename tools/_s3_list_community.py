"""
S3 community 이미지 목록 확인 + Render DB 현황 점검
"""
import os, sys
sys.path.insert(0, r"Q:\Claudework\bridge base")

# S3 credentials from environment or vault
try:
    from tools import bx as bx_mod
    bx_mod.cmd_load()  # load all MANAGED keys into os.environ
    print(f"[BX] Credentials loaded into env")
except Exception as e:
    print(f"[BX] Failed: {e}")

AWS_ACCESS_KEY_ID     = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_S3_BUCKET         = os.environ.get("AWS_S3_BUCKET")
AWS_REGION            = os.environ.get("AWS_REGION", "ap-northeast-2")
print(f"[INFO] Bucket: {AWS_S3_BUCKET}, Region: {AWS_REGION}")

if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET]):
    print("ERROR: S3 credentials not available")
    sys.exit(1)

import boto3
from botocore.exceptions import ClientError

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

# List community/ objects
print("\n=== S3 community/ objects ===")
try:
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=AWS_S3_BUCKET, Prefix="community/")
    count = 0
    for page in pages:
        for obj in page.get("Contents", []):
            print(f"  {obj['Key']}  ({obj['Size']} bytes)  {obj['LastModified'].strftime('%Y-%m-%d')}")
            count += 1
    print(f"Total: {count} community objects")
except Exception as e:
    print(f"ERROR listing S3: {e}")
