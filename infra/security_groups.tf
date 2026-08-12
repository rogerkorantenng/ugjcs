# Attached to the App Runner VPC connector's ENIs. No inbound rule is needed — App
# Runner reaches this group's members outbound only, over the connector.
resource "aws_security_group" "apprunner_connector" {
  name        = "ugjcs-apprunner-connector"
  description = "Egress-only group for the App Runner VPC connector"
  vpc_id      = data.aws_vpc.default.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# RDS accepts Postgres traffic from the App Runner connector's security group only —
# this, plus publicly_accessible = false on the instance itself, is what "not publicly
# accessible" means concretely.
resource "aws_security_group" "rds" {
  name        = "ugjcs-rds"
  description = "PostgreSQL reachable only from the App Runner VPC connector"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.apprunner_connector.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
