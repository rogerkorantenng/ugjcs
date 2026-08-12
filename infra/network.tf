# No bespoke VPC. RDS and the App Runner VPC connector sit in the account's default VPC
# and its existing subnets, read via data sources rather than provisioned.
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# App Runner VPC connectors do not support every Availability Zone that the default VPC
# spans — this account's default VPC includes an AZ (use1-az3 / us-east-1e) that
# CreateVpcConnector rejects with "don't support App Runner services". RDS has no such
# restriction, so its subnet group (infra/rds.tf) still uses the full default-VPC subnet
# list; only the connector below needs the filtered set.
data "aws_subnet" "default" {
  for_each = toset(data.aws_subnets.default.ids)
  id       = each.value
}

locals {
  apprunner_connector_subnet_ids = [
    for s in data.aws_subnet.default : s.id
    if s.availability_zone_id != "use1-az3"
  ]
}
