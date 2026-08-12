output "ecr_repository_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "s3_bucket_name" {
  value = aws_s3_bucket.manuscripts.bucket
}

output "jwt_secret_arn" {
  value = aws_secretsmanager_secret.jwt_secret.arn
}

output "database_url_secret_arn" {
  value = aws_secretsmanager_secret.database_url.arn
}

output "rds_endpoint" {
  value     = aws_db_instance.postgres.endpoint
  sensitive = true
}

output "apprunner_vpc_connector_arn" {
  value = aws_apprunner_vpc_connector.connector.arn
}
