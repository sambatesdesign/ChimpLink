# storage_utils.py

import os
import json
import boto3
from botocore.exceptions import NoCredentialsError

APP_ENV = os.getenv("APP_ENV", "local")
USE_SPACES = APP_ENV == "production"

DO_BUCKET = os.getenv("DIGITALOCEAN_SPACE_BUCKET", "keepabl-com")
DO_REGION = os.getenv("DIGITALOCEAN_SPACE_REGION", "nyc3")
DO_FOLDER = os.getenv("DIGITALOCEAN_SPACE_FOLDER", "webhook_logs")
DO_ENDPOINT = f"https://{DO_REGION}.digitaloceanspaces.com"
DO_ID = os.getenv("DIGITALOCEAN_SPACE_KEY")
DO_SECRET = os.getenv("DIGITALOCEAN_SPACE_SECRET")

def _get_s3_client():
    print("👀 SPACE_KEY:", DO_ID)
    print("👀 SPACE_SECRET:", "SET" if DO_SECRET else "MISSING")
    return boto3.client(
        "s3",
        region_name=DO_REGION,
        endpoint_url=DO_ENDPOINT,
        aws_access_key_id=DO_ID,
        aws_secret_access_key=DO_SECRET
    )

def load_json(filename):
    if USE_SPACES:
        try:
            client = _get_s3_client()
            key = f"{DO_FOLDER}/{filename}"
            response = client.get_object(Bucket=DO_BUCKET, Key=key)
            return json.loads(response["Body"].read().decode())
        except Exception as e:
            print(f"⚠️ Failed to load {filename} from Spaces: {e}")
            return {}
    else:
        if os.path.exists(filename):
            try:
                with open(filename, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Failed to read {filename}: {e}")
        return {}

def save_json(filename, data):
    if USE_SPACES:
        try:
            client = _get_s3_client()
            key = f"{DO_FOLDER}/{filename}"
            client.put_object(Bucket=DO_BUCKET, Key=key, Body=json.dumps(data, indent=2))
        except Exception as e:
            print(f"⚠️ Failed to write {filename} to Spaces: {e}")
    else:
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to write {filename} locally: {e}")

# 🔄 New helper for loading the merge field mappings
def load_merge_map():
    return load_json("merge_map.json")
