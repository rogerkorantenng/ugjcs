# NOT APPLIED. Rename this file to apprunner_service.tf once an image tagged `latest`
# exists in the ugjcs-backend ECR repository (App Runner requires the image to exist
# before the service resource can be created — there is no chicken-and-egg option here).
# Then run `terraform apply` again.

resource "aws_apprunner_service" "api" {
  service_name = "ugjcs-backend"

  source_configuration {
    auto_deployments_enabled = false # deploy workflow triggers deployments explicitly

    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_ecr_access.arn
    }

    image_repository {
      image_identifier      = "${aws_ecr_repository.backend.repository_url}:latest"
      image_repository_type = "ECR"

      image_configuration {
        port = "8000"
        runtime_environment_secrets = {
          UGJCS_DATABASE_URL = aws_secretsmanager_secret.database_url.arn
          UGJCS_JWT_SECRET   = aws_secretsmanager_secret.jwt_secret.arn
        }
      }
    }
  }

  instance_configuration {
    # Smallest App Runner size: 0.25 vCPU / 0.5 GB, about USD 14/month against roughly
    # USD 57 for 1 vCPU / 2 GB. App Runner bills provisioned capacity continuously because
    # the health check keeps the instance active, so this is the difference between a
    # ~USD 29/month total and ~USD 72 — well outside the accepted range for a workload that
    # serves an examiner and a seeded demonstration corpus. Raise it if load ever justifies it.
    cpu               = "256"
    memory            = "512"
    instance_role_arn = aws_iam_role.apprunner_instance.arn
  }

  network_configuration {
    egress_configuration {
      egress_type       = "VPC"
      vpc_connector_arn = aws_apprunner_vpc_connector.connector.arn
    }
  }

  health_check_configuration {
    protocol            = "HTTP"
    path                = "/health"
    interval            = 10
    timeout             = 5
    healthy_threshold   = 1
    unhealthy_threshold = 5
  }

  depends_on = [aws_secretsmanager_secret_version.database_url]
}

output "apprunner_service_url" {
  value = "https://${aws_apprunner_service.api.service_url}"
}

output "apprunner_service_arn" {
  value = aws_apprunner_service.api.arn
}
