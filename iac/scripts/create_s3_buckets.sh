#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Create the medallion buckets (Bronze/Silver/Gold) on the configured S3
# endpoint. Works against MinIO (dev) or AWS S3 (prod) via the AWS CLI.
# Idempotent: ignores "bucket already exists".
#
# Usage (from repo root, with .env loaded):
#   bash iac/scripts/create_s3_buckets.sh
# -----------------------------------------------------------------------------
set -euo pipefail

ENDPOINT="${S3_PUBLIC_ENDPOINT_URL:-${S3_ENDPOINT_URL:-http://localhost:9000}}"
REGION="${AWS_REGION:-eu-north-1}"

buckets=(
    "${S3_BRONZE_BUCKET:-homepedia-bronze}"
    "${S3_SILVER_BUCKET:-homepedia-silver}"
    "${S3_GOLD_BUCKET:-homepedia-gold}"
)

for b in "${buckets[@]}"; do
    if aws --endpoint-url "$ENDPOINT" s3api head-bucket --bucket "$b" >/dev/null 2>&1; then
        echo "  = $b (already exists)"
    else
        aws --endpoint-url "$ENDPOINT" s3api create-bucket \
            --bucket "$b" \
            --create-bucket-configuration "LocationConstraint=$REGION" >/dev/null 2>&1 \
        || aws --endpoint-url "$ENDPOINT" s3api create-bucket --bucket "$b" >/dev/null
        echo "  + $b (created)"
    fi
done

echo "create_s3_buckets: done against $ENDPOINT"
