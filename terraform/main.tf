terraform {
    required_providers {
        aws = {
            source  = "hashicorp/aws"
            version = "~>5.0"
        }
    }
}

# tflocal automatically redirects these calls to http://localhost:4566.
# To use real AWS: remove the skip_* flags and supply real credentials via env vars.
provider "aws" {
    region     = "us-east-1"
    access_key = "test"
    secret_key = "test"

    skip_credentials_validation = true
    skip_metadata_api_check     = true
    skip_requesting_account_id  = true
}

# The S3 bucket where all uploaded PDFs are stored
resource "aws_s3_bucket" "pdfs" {
    bucket = var.bucket_name
}

# Block all public access --- only the app inside Docker Compose can reach this bucket
resource "aws_s3_bucket_public_access_block" "pdfs" {
    bucket = aws_s3_bucket.pdfs.id

    block_public_acls       = true
    block_public_policy     = true
    ignore_public_acls      = true
    restrict_public_buckets = true
}

# Outputs --- printed after tflocal apply so you can verify what was created
output "bucket_name" {
    value       = aws_s3_bucket.pdfs.bucket
    description = "S3 bucket name for uploaded PDFs"
}
