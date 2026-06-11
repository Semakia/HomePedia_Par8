"""S3/MinIO loader for the Bronze layer.

Bronze is the immutable landing zone: raw bytes are stored as-is, partitioned by
dataset, and accompanied by a `_manifest.json` capturing provenance (source URL,
fetch time, size, sha256). Downstream Silver jobs read from here, never the source.

Key convention:
    {dataset}/{partition...}/{filename}
    e.g. dvf/year=2024/full.csv.gz
         dvf/year=2024/departement=75/75.csv.gz
Manifest sits next to the object: {same prefix}/_manifest.json
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from src.data_ingestion.utils.logging_utils import get_logger

log = get_logger(__name__)


def bronze_key(dataset: str, filename: str, **partitions: str | int) -> str:
    """
        Build a Hive-style partitioned object key.

        Args:
            dataset : top-level dataset name (e.g. "dvf")
            filename : name of the file (e.g. "full.csv.gz")
            partitions : optional partition key-values (e.g. year=2024, departement=75)

        Returns: the full object key (e.g. "dvf/year=2024/departement=75/75.csv.gz")

        >>> bronze_key("dvf", "full.csv.gz", year=2024)
        'dvf/year=2024/full.csv.gz'
        >>> bronze_key("dvf", "75.csv.gz", year=2024, departement="75")
        'dvf/year=2024/departement=75/75.csv.gz'
    """
    parts = [dataset.strip("/")]
    parts += [f"{k}={v}" for k, v in partitions.items()]
    parts.append(filename)
    return "/".join(parts)


@dataclass
class S3Loader:
    """S3 writer that targets either MinIO (dev) or Amazon S3 (prod).

    The target is decided by config, not code:
      - `endpoint_url` set (e.g. http://localhost:9000) -> MinIO/custom S3,
        path-style addressing.
      - `endpoint_url` None/empty -> real AWS S3, virtual-hosted addressing.
      - `access_key`/`secret_key` None -> fall back to the default AWS
        credential chain (env vars, ~/.aws/credentials, SSO, IAM role).
    """

    endpoint_url: str | None = None
    access_key: str | None = None
    secret_key: str | None = None
    region: str = "eu-west-3"

    def __post_init__(self) -> None:
        # Path-style is required by MinIO; AWS defaults to virtual-hosted.
        addressing = "path" if self.endpoint_url else "auto"
        self._client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url or None,
            aws_access_key_id=self.access_key or None,
            aws_secret_access_key=self.secret_key or None,
            region_name=self.region,
            config=Config(
                signature_version="s3v4", s3={"addressing_style": addressing}
            ),
        )
        log.info(
            "s3.client.ready",
            target="aws" if not self.endpoint_url else self.endpoint_url,
            region=self.region,
        )

    @classmethod
    def from_env(cls) -> "S3Loader":
        # Empty string -> None so boto3 uses AWS defaults / credential chain.
        return cls(
            endpoint_url=os.getenv("S3_ENDPOINT_URL") or None,
            access_key=os.getenv("AWS_ACCESS_KEY_ID") or None,
            secret_key=os.getenv("AWS_SECRET_ACCESS_KEY") or None,
            region=os.getenv("AWS_REGION", "eu-west-3"),
        )

    # --- bucket helpers ----------------------------------------------------
    def ensure_bucket(self, bucket: str) -> None:
        """Create the bucket if missing. Tolerant: on AWS, buckets are usually
        provisioned by IaC, so a creation failure is logged, not raised — the
        first upload will surface a clear error if the bucket truly is missing.
        """
        try:
            self._client.head_bucket(Bucket=bucket)
            return
        except ClientError:
            pass

        params: dict = {"Bucket": bucket}
        # AWS requires a LocationConstraint for every region except us-east-1.
        # MinIO accepts a plain create, so only add it for real AWS.
        if not self.endpoint_url and self.region and self.region != "us-east-1":
            params["CreateBucketConfiguration"] = {"LocationConstraint": self.region}
        try:
            log.info("s3.create_bucket", bucket=bucket)
            self._client.create_bucket(**params)
        except ClientError as exc:
            log.warning("s3.create_bucket.skip", bucket=bucket, error=str(exc))

    def object_exists(self, bucket: str, key: str) -> bool:
        try:
            self._client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError:
            return False

    # --- writes ------------------------------------------------------------
    def upload_file(
        self,
        bucket: str,
        key: str,
        local_path: str,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> str:
        """
            Upload a local file (multipart under the hood). Returns the s3 URI.
            Args:
                - bucket : target bucket name
                - key : target object key (path within the bucket)
                - local_path : path to the local file to upload
                - content_type : MIME type of the file (default: application/octet-stream)
                - metadata : optional user metadata to attach to the object (dict of string key-values)
            Returns: the s3 URI of the uploaded object (e.g. "s3://my-bucket/path
        """
        extra = {"ContentType": content_type}
        if metadata:
            # S3 user-metadata values must be strings.
            extra["Metadata"] = {k: str(v) for k, v in metadata.items()}
        self._client.upload_file(local_path, bucket, key, ExtraArgs=extra)
        uri = f"s3://{bucket}/{key}"
        log.info("s3.upload_file", uri=uri, content_type=content_type)
        return uri

    def put_json(self, bucket: str, key: str, obj: dict) -> str:
        """
            Serialize a dict as JSON and upload it to S3. Returns the s3 URI.
            Args:
                - bucket : target bucket name
                - key : target object key (path within the bucket)
                - obj : the dict to serialize and upload
            Returns: the s3 URI of the uploaded object
        """
        body = json.dumps(obj, indent=2, ensure_ascii=False).encode("utf-8")
        self._client.put_object(
            Bucket=bucket, Key=key, Body=body, ContentType="application/json"
        )
        uri = f"s3://{bucket}/{key}"
        log.info("s3.put_json", uri=uri, bytes=len(body))
        return uri
