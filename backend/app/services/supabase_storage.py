import os
import logging
from typing import Optional, Dict, Any, Union
from supabase import create_client, Client
from app.core.config import settings

logger = logging.getLogger(__name__)

class SupabaseStorageService:
    """
    Manages interactions with Supabase private storage buckets:
    - Secure binary uploads for images, video, audio, reports, and artifacts.
    - Generating short-lived signed URLs for authorized viewing and downloading.
    - Local fallback gracefully when Supabase credentials are not configured.
    """
    def __init__(self):
        self.client: Optional[Client] = None
        self.bucket: str = settings.SUPABASE_STORAGE_BUCKET
        self._init_client()

    def _init_client(self):
        url = settings.SUPABASE_URL
        # Prefer service role key on backend to perform administrative storage actions (bypassing public policies)
        key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY
        if url and key:
            try:
                self.client = create_client(url, key)
                logger.info(f"Connected to Supabase client at {url} (Bucket: {self.bucket})")
            except Exception as e:
                logger.warning(f"Failed to initialize Supabase client: {e}")
                self.client = None
        else:
            logger.info("Supabase credentials not fully configured; using local filesystem storage fallback.")

    @property
    def is_configured(self) -> bool:
        return self.client is not None

    def upload_file(
        self,
        local_path: str,
        storage_destination: str,
        content_type: str = "application/octet-stream"
    ) -> Optional[str]:
        """
        Uploads a local file to the private Supabase storage bucket.
        Returns the object storage path (e.g. 'analyses/<id>/original.jpg') or None on failure.
        """
        if not self.client:
            return None

        if not os.path.exists(local_path):
            logger.warning(f"Cannot upload non-existent local file: {local_path}")
            return None

        try:
            with open(local_path, "rb") as f:
                file_bytes = f.read()

            res = self.client.storage.from_(self.bucket).upload(
                path=storage_destination,
                file=file_bytes,
                file_options={"content-type": content_type, "upsert": "true"}
            )
            logger.info(f"Uploaded {local_path} to Supabase storage '{storage_destination}'")
            return storage_destination
        except Exception as e:
            logger.error(f"Error uploading {local_path} to Supabase storage: {e}")
            return None

    def upload_bytes(
        self,
        data: bytes,
        storage_destination: str,
        content_type: str = "application/octet-stream"
    ) -> Optional[str]:
        """
        Uploads in-memory bytes to the private Supabase storage bucket.
        """
        if not self.client:
            return None

        try:
            self.client.storage.from_(self.bucket).upload(
                path=storage_destination,
                file=data,
                file_options={"content-type": content_type, "upsert": "true"}
            )
            logger.info(f"Uploaded bytes ({len(data)} B) to Supabase storage '{storage_destination}'")
            return storage_destination
        except Exception as e:
            logger.error(f"Error uploading bytes to Supabase storage: {e}")
            return None

    def create_signed_url(
        self,
        storage_path: str,
        expires_in: int = 3600
    ) -> Optional[str]:
        """
        Generates a secure, short-lived signed URL for private bucket access.
        Default expiration: 1 hour (3600 seconds).
        """
        if not self.client or not storage_path:
            return None

        try:
            res = self.client.storage.from_(self.bucket).create_signed_url(
                path=storage_path,
                expires_in=expires_in
            )
            # res is usually a dict {'signedURL': '...'} or object with signedURL/signed_url
            if isinstance(res, dict):
                return res.get("signedURL") or res.get("signed_url")
            elif hasattr(res, "signed_url"):
                return res.signed_url
            elif hasattr(res, "signedURL"):
                return res.signedURL
            return str(res)
        except Exception as e:
            logger.warning(f"Failed to generate signed URL for '{storage_path}': {e}")
            return None

    def download_file(self, storage_path: str) -> Optional[bytes]:
        """
        Downloads a private file from Supabase storage into memory bytes.
        """
        if not self.client or not storage_path:
            return None

        try:
            return self.client.storage.from_(self.bucket).download(storage_path)
        except Exception as e:
            logger.error(f"Error downloading '{storage_path}' from Supabase: {e}")
            return None

supabase_storage = SupabaseStorageService()
