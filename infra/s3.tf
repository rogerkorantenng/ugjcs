resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "manuscripts" {
  bucket = "ugjcs-manuscripts-${random_id.bucket_suffix.hex}"
}

resource "aws_s3_bucket_public_access_block" "manuscripts" {
  bucket                  = aws_s3_bucket.manuscripts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "manuscripts" {
  bucket = aws_s3_bucket.manuscripts.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "manuscripts" {
  bucket = aws_s3_bucket.manuscripts.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Every document a reviewer or reader retrieves is reached through a pre-signed URL
# issued by the application, never a bucket policy grant — that is what "all public
# access blocked" buys: even a misconfigured application-layer bug cannot make an object
# world readable, because the bucket itself refuses to allow it.
resource "aws_s3_bucket_lifecycle_configuration" "manuscripts" {
  bucket = aws_s3_bucket.manuscripts.id

  rule {
    id     = "expire-noncurrent-versions"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}
