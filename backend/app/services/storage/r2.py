"""Cloudflare R2 (S3-compatible) storage backend."""

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError

from app.services.storage.base import StorageBackend
from app.utils.errors import APIError


class R2Storage(StorageBackend):
    """Stores media files in a private Cloudflare R2 bucket with presigned URLs."""

    def __init__(
        self,
        endpoint_url: str,
        bucket_name: str,
        access_key_id: str,
        secret_access_key: str,
        presigned_expiry: int = 3600,
    ) -> None:
        self.bucket_name = bucket_name
        self.presigned_expiry = presigned_expiry
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url.rstrip("/"),
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name="auto",
            config=BotoConfig(signature_version="s3v4"),
        )

    def save(self, key: str, data: bytes, content_type: str = "image/webp") -> str:
        """Upload file bytes to Cloudflare R2 and return the storage key."""
        clean_key = key.lstrip("/")
        try:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=clean_key,
                Body=data,
                ContentType=content_type,
            )
            return clean_key
        except (ClientError, BotoCoreError) as exc:
            raise APIError(
                502, "STORAGE_UPLOAD_FAILED", "Failed to upload file to R2 storage"
            ) from exc

    def delete(self, key: str) -> None:
        """Delete an object from Cloudflare R2."""
        clean_key = key.lstrip("/")
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=clean_key)
        except (ClientError, BotoCoreError) as exc:
            raise APIError(
                502, "STORAGE_DELETE_FAILED", "Failed to delete file from R2 storage"
            ) from exc

    def get_url(self, key: str) -> str:
        """Generate a short-lived presigned GET URL for private R2 bucket access."""
        clean_key = key.lstrip("/")
        try:
            return self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": clean_key},
                ExpiresIn=self.presigned_expiry,
            )
        except (ClientError, BotoCoreError) as exc:
            raise APIError(
                502, "STORAGE_URL_FAILED", "Failed to generate presigned R2 URL"
            ) from exc
