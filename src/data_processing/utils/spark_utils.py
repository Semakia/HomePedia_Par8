"""Spark helpers for the Silver layer.

Builds a SparkSession wired for S3A access that targets either MinIO (dev) or
Amazon S3 (prod) — same code, switched by env, mirroring src/data_ingestion's
S3Loader:
  - S3_ENDPOINT_URL set  -> MinIO/custom, path-style, plain HTTP if http://
  - S3_ENDPOINT_URL empty -> real AWS S3 (default endpoint, virtual-hosted)
  - AWS_* creds present   -> SimpleAWSCredentialsProvider, else default chain

The hadoop-aws / aws-sdk jars ship in the Spark image (see
iac/docker/dev/spark/Dockerfile), so no --packages is needed at submit time.
"""

from __future__ import annotations

import os

from pyspark.sql import SparkSession


def build_spark(
    app_name: str = "homepedia-silver"
) -> SparkSession:
    """
    Build a SparkSession configured for S3A access.
    The target (MinIO vs AWS) is decided by env, not code:
      - `endpoint_url` set (e.g. http://localhost:9000) -> MinIO/custom S3,
        path-style addressing.
      - `endpoint_url` None/empty -> real AWS S3, virtual-hosted addressing.
      - `access_key`/`secret_key` None -> fall back to the default AWS
        credential chain (env vars, ~/.aws/credentials, SSO, IAM role).
    """

    endpoint = os.getenv("S3_ENDPOINT_URL") or ""
    access_key = os.getenv("AWS_ACCESS_KEY_ID") or ""
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY") or ""
    region = os.getenv("AWS_REGION") or "eu-west-3"

    builder = (
        SparkSession.builder.appName(app_name)
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        # Overwrite only the partitions we write, keep the others intact.
        .config("spark.sql.sources.partitionOverwriteMode", "dynamic")
        .config("spark.sql.parquet.compression.codec", "snappy")
        # Keep partition columns as strings on read; otherwise Spark infers
        # code_departement as int and breaks Corsica (2A/2B) and DOM (971...).
        .config("spark.sql.sources.partitionColumnTypeInference.enabled", "false")
    )

    if access_key and secret_key:
        builder = (
            builder.config("spark.hadoop.fs.s3a.access.key", access_key)
            .config("spark.hadoop.fs.s3a.secret.key", secret_key)
            .config(
                "spark.hadoop.fs.s3a.aws.credentials.provider",
                "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider",
            )
        )
    else:
        # No static keys -> let the default AWS chain resolve (IAM role, etc.).
        builder = builder.config(
            "spark.hadoop.fs.s3a.aws.credentials.provider",
            "com.amazonaws.auth.DefaultAWSCredentialsProviderChain",
        )

    if endpoint:
        # MinIO / custom S3: explicit endpoint + path-style addressing.
        builder = (
            builder.config("spark.hadoop.fs.s3a.endpoint", endpoint)
            .config("spark.hadoop.fs.s3a.path.style.access", "true")
            .config(
                "spark.hadoop.fs.s3a.connection.ssl.enabled",
                "true" if endpoint.startswith("https") else "false",
            )
        )
    else:
        # Real AWS: pin the regional endpoint, otherwise hadoop-aws hits the
        # global (us-east-1) endpoint and a non-us-east-1 bucket fails with
        # PermanentRedirect.
        builder = builder.config(
            "spark.hadoop.fs.s3a.endpoint", f"s3.{region}.amazonaws.com"
        ).config("spark.hadoop.fs.s3a.endpoint.region", region)

    return builder.getOrCreate()


def build_s3a_uri(
    bucket: str,
    *parts: str
) -> str:
    """
    Build an s3a:// URI from a bucket and path parts.
    """
    path = "/".join(p.strip("/") for p in parts if p)
    return f"s3a://{bucket}/{path}" if path else f"s3a://{bucket}"
