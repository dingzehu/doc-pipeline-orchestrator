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

# IAM user that Django and Celery will authenticate as
resource "aws_iam_user" "app" {
    name = "doc-pipeline-app"
}

# Least-privilege policy --- only allows reading and writing objects in this bucket
resource "aws_iam_policy" "s3_access" {
    name        = "doc-pipeline-s3-access"
    description = "Allow doc-pipeline-app to read and write PDFs in the bucket"

    policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
            {
                Effect   = "Allow"
                Action   = ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"]
                Resource = "${aws_s3_bucket.pdfs.arn}/*"  # objects inside the bucket only
            },
            {
                Effect   = "Allow"
                Action   = ["s3:ListBucket"]
                Resource = aws_s3_bucket.pdfs.arn    # the bucket itself (needed for the list)

            }
        ]
    })
}

# Attach the policy to the IAM user
resource "aws_iam_user_policy_attachment" "app_s3" {
    user       = aws_iam_user.app.name
    policy_arn = aws_iam_policy.s3_access.arn
}

# Outputs --- printed after tflocal apply so you can verify what was created
output "bucket_name" {
    value       = aws_s3_bucket.pdfs.bucket
    description = "S3 bucket name for uploaded PDFs"
}

output "iam_user" {
    value       = aws_iam_user.app.name
    description = "IAM user that has read/write access to the bucket"
}