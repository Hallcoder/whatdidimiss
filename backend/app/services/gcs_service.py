from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path

from google.cloud import storage

from app.config import settings
from app.utils.exceptions import GCSError

logger = logging.getLogger(__name__)


class GCSService:
    def __init__(self):
        self._client: storage.Client | None = None

    @property
    def client(self) -> storage.Client:
        if self._client is None:
            self._client = storage.Client(project=settings.gcp_project_id)
        return self._client

    @property
    def bucket(self) -> storage.Bucket:
        return self.client.bucket(settings.gcs_bucket_name)

    def upload_file(self, local_path: Path, destination_blob: str) -> str:
        """Upload a local file to GCS and return the gs:// URI."""
        try:
            blob = self.bucket.blob(destination_blob)
            blob.upload_from_filename(str(local_path))
            gcs_uri = f"gs://{settings.gcs_bucket_name}/{destination_blob}"
            logger.info("Uploaded %s to %s", local_path, gcs_uri)
            return gcs_uri
        except Exception as e:
            raise GCSError(
                message=f"Failed to upload file to GCS: {e}",
                details={"local_path": str(local_path), "destination": destination_blob},
            )

    def delete_blob(self, gcs_uri: str) -> None:
        """Delete a blob from GCS given its gs:// URI."""
        try:
            blob_name = gcs_uri.replace(f"gs://{settings.gcs_bucket_name}/", "")
            blob = self.bucket.blob(blob_name)
            blob.delete()
            logger.info("Deleted %s", gcs_uri)
        except Exception as e:
            raise GCSError(
                message=f"Failed to delete blob from GCS: {e}",
                details={"gcs_uri": gcs_uri},
            )

    def generate_signed_url(self, gcs_uri: str, expiration_minutes: int = 60) -> str:
        """Generate a signed URL for temporary access to a GCS object."""
        try:
            blob_name = gcs_uri.replace(f"gs://{settings.gcs_bucket_name}/", "")
            blob = self.bucket.blob(blob_name)
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=expiration_minutes),
                method="GET",
            )
            return url
        except Exception as e:
            raise GCSError(
                message=f"Failed to generate signed URL: {e}",
                details={"gcs_uri": gcs_uri},
            )
