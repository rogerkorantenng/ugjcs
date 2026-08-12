resource "aws_apprunner_vpc_connector" "connector" {
  vpc_connector_name = "ugjcs-connector"
  subnets            = local.apprunner_connector_subnet_ids
  security_groups    = [aws_security_group.apprunner_connector.id]
}

# The aws_apprunner_service resource is intentionally NOT here. App Runner requires the
# ECR image to already exist before the service can be created, and no backend image has
# been built yet (that is a separate, not-yet-landed task). The service definition is
# written in full in infra/apprunner_service.tf.disabled — a file Terraform never reads
# (it does not end in .tf) — ready to be renamed to infra/apprunner_service.tf and applied
# once `ugjcs-backend:latest` exists in ECR.
