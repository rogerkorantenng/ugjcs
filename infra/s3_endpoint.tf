# App Runner reaches the database through the VPC connector, but that connector's network
# interfaces have no public address. S3 is a public endpoint, so without a route the container
# has permission to write objects and no way to reach them — an upload simply hangs until the
# request times out and the health check kills the instance.
#
# A gateway endpoint puts S3 on the VPC's route tables directly. It costs nothing, keeps the
# traffic off the public internet entirely, and is the reason this works at all.

data "aws_route_tables" "default" {
  vpc_id = data.aws_vpc.default.id
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = data.aws_vpc.default.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = data.aws_route_tables.default.ids

  tags = { Name = "ugjcs-s3" }
}
