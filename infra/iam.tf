# Lets App Runner's build service pull the private image from ECR.
data "aws_iam_policy_document" "apprunner_build_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["build.apprunner.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "apprunner_ecr_access" {
  name               = "ugjcs-apprunner-ecr-access"
  assume_role_policy = data.aws_iam_policy_document.apprunner_build_trust.json
}

resource "aws_iam_role_policy_attachment" "apprunner_ecr_access" {
  role       = aws_iam_role.apprunner_ecr_access.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

# Lets the running container read its two secrets and use pre-signed S3 URLs.
data "aws_iam_policy_document" "apprunner_instance_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["tasks.apprunner.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "apprunner_instance" {
  name               = "ugjcs-apprunner-instance"
  assume_role_policy = data.aws_iam_policy_document.apprunner_instance_trust.json
}

data "aws_iam_policy_document" "apprunner_instance_permissions" {
  statement {
    sid     = "ReadRuntimeSecrets"
    actions = ["secretsmanager:GetSecretValue"]
    resources = [
      aws_secretsmanager_secret.database_url.arn,
      aws_secretsmanager_secret.jwt_secret.arn,
    ]
  }

  statement {
    sid       = "PresignedDocumentAccess"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.manuscripts.arn}/*"]
  }

  statement {
    sid       = "ListDocumentBucket"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.manuscripts.arn]
  }
}

resource "aws_iam_role_policy" "apprunner_instance" {
  name   = "ugjcs-apprunner-instance-permissions"
  role   = aws_iam_role.apprunner_instance.id
  policy = data.aws_iam_policy_document.apprunner_instance_permissions.json
}
