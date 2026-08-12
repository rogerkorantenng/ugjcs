resource "aws_db_subnet_group" "postgres" {
  name       = "ugjcs-db-subnet-group"
  subnet_ids = data.aws_subnets.default.ids
}

# The RDS master password: generated here and stored straight into Secrets Manager
# (infra/secrets.tf). It never appears in a literal, an output, or a log.
resource "random_password" "db_password" {
  length  = 32
  special = false
}

resource "aws_db_instance" "postgres" {
  identifier     = "ugjcs-postgres"
  engine         = "postgres"
  engine_version = "16"
  instance_class = var.db_instance_class

  allocated_storage = 20
  storage_type      = "gp3"

  db_name  = var.db_name
  username = var.db_username
  password = random_password.db_password.result

  db_subnet_group_name   = aws_db_subnet_group.postgres.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  # This, together with the security group in infra/security_groups.tf, is what "not
  # publicly accessible" means: no public IP is assigned, AND only the App Runner
  # connector's security group may reach port 5432.
  publicly_accessible = false

  multi_az                = false
  backup_retention_period = 1
  skip_final_snapshot     = true
  deletion_protection     = false
  apply_immediately       = true
}
