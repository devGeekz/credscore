import uuid

import boto3
from botocore.client import Config

from app.config import settings


def _get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.storage_endpoint or None,  # None -> real AWS S3
        aws_access_key_id=settings.storage_access_key,
        aws_secret_access_key=settings.storage_secret_key,
        config=Config(signature_version="s3v4"),
    )


def upload_statement_file(file_bytes: bytes, filename: str, tenant_id: str) -> str:
    """Uploads a raw statement file and returns its object key (not a URL)."""
    extension = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
    object_key = f"statements/{tenant_id}/{uuid.uuid4()}.{extension}"

    client = _get_s3_client()
    client.put_object(
        Bucket=settings.storage_bucket,
        Key=object_key,
        Body=file_bytes,
        # ServerSideEncryption="AES256",
    )
    return object_key


def generate_download_url(object_key: str, expires_in: int = 3600) -> str:
    """Signed, expiring URL for one-time access — default 1 hour."""
    client = _get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.storage_bucket, "Key": object_key},
        ExpiresIn=expires_in,
    )