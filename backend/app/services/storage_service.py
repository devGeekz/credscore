import uuid
from pathlib import Path

import boto3
from botocore.client import Config

from app.config import settings

# local-disk fallback so dev works without r2/s3 creds —
# set STORAGE_BUCKET to switch to object storage.
LOCAL_STORAGE_DIR = Path(__file__).resolve().parents[2] / "storage"


def s3_configured() -> bool:
    return bool(settings.storage_bucket and settings.storage_endpoint)


def _get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.storage_endpoint or None,  # None -> real aws s3
        aws_access_key_id=settings.storage_access_key,
        aws_secret_access_key=settings.storage_secret_key,
        config=Config(signature_version="s3v4"),
    )


def upload_statement_file(file_bytes: bytes, filename: str, tenant_id: str) -> str:
    """uploads a raw statement file and returns its object key (not a url)."""
    extension = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
    object_key = f"statements/{tenant_id}/{uuid.uuid4()}.{extension}"

    if not s3_configured():
        path = LOCAL_STORAGE_DIR / object_key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(file_bytes)
        return object_key

    client = _get_s3_client()
    client.put_object(
        Bucket=settings.storage_bucket,
        Key=object_key,
        Body=file_bytes,
        ServerSideEncryption="AES256",
    )
    return object_key


def download_statement_file(object_key: str) -> bytes:
    if not s3_configured():
        return (LOCAL_STORAGE_DIR / object_key).read_bytes()

    client = _get_s3_client()
    response = client.get_object(Bucket=settings.storage_bucket, Key=object_key)
    return response["Body"].read()


def generate_download_url(object_key: str, expires_in: int = 3600) -> str:
    """signed, expiring url for one-time access — default 1 hour.
    s3-only; the local/encrypted equivalent is not implemented."""
    client = _get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.storage_bucket, "Key": object_key},
        ExpiresIn=expires_in,
    )
