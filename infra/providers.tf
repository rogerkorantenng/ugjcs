# Local state only. This is a single-developer, 48-hour project — a remote backend
# (S3 + DynamoDB locking) is the correct answer for a team, but there is exactly one
# operator against a deadline here, so state is kept on disk and excluded from git via
# infra/.gitignore. Do not lose infra/terraform.tfstate; it is the only record of what
# was actually provisioned.
terraform {
  required_version = ">= 1.10.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

# No `profile` is set: per TD-01 (docs/04-technical-debt-register.md), this project
# deliberately runs on AWS root credentials from the already-authenticated local CLI
# rather than a scoped IAM deploy user. Deployment is run locally, never from CI, and no
# credential is ever placed in GitHub Actions secrets.
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      project = "ugjcs"
    }
  }
}
