variable "bucket_name" {
    description = "Name of the S3 bucket used to store uploaded PDFs"
    type        = string
    default     = "doc-pipeline-pdfs"
}