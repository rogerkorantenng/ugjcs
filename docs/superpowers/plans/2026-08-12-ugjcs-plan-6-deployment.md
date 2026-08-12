# UGJCS Plan 6 — Deployment and Infrastructure

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the backend and frontend built by Plans 1–5 into a live application an examiner can open over HTTPS, with admin and test credentials that work, on infrastructure provisioned by a scoped IAM principal rather than the AWS root account. Deployment is 3 of 50 marks and is currently zero; this plan is what earns it.

## Why this is smaller than the specification

`docs/superpowers/specs/2026-08-12-ugjcs-journal-platform-design.md` §7.3 designs the
backend behind ECS Fargate, an Application Load Balancer, and CloudFront — a topology
that is architecturally sound and is assessed on its own merits wherever the spec is
read. That design stands; it is not being revised here.

What changed is what gets *provisioned*. Standing up ECS/ALB/CloudFront — a VPC, public
and private subnets, an ALB with a target group and listener rules, a CloudFront
distribution, an ECS cluster, task definitions and a service, and the IAM wiring between
all of it — measured at **4–6 hours** against a 48-hour project budget that, at the point
this trade-off was made, still owed a working API, a working frontend, and five
accompanying documents. Spending a quarter of the remaining time on infrastructure the
brief does not grade line-by-line was not a good trade.

**AWS App Runner delivers the identical application over the identical TLS guarantee in
a fraction of that time.** CloudFront's job in §7.3 was never decorative: it supplies a
trusted certificate on a public hostname so an HTTPS Vercel frontend can call the backend
without a registered domain. App Runner supplies exactly that — a trusted certificate on
a `*.awsapprunner.com` hostname — as a property of the service itself, with no
distribution, no ALB, and no listener rules to write. Nobody should read the absence of
CloudFront below as an oversight; it is replaced, not dropped, and §"Architecture" states
that explicitly.

The gap between what was designed and what is deployed is recorded honestly as
**Scheduled technical debt** with a bounded repayment (TD-14, appended to
`docs/04-technical-debt-register.md` by this same plan): the ECS/ALB/CloudFront stack
remains buildable from the existing spec once the document and feature backlog this
budget was actually protecting is clear.

**Architecture:**

```
Reader ─▶ Vercel (Next.js, BFF) ─▶ HTTPS ─▶ App Runner (FastAPI container)
                                              *.awsapprunner.com — trusted TLS,
                                              no registered domain needed
                                                   │
                                    VPC connector (default VPC, no NAT)
                                                   │
                                   ┌───────────────┴───────────────┐
                                   ▼                                ▼
                      RDS PostgreSQL db.t4g.micro         S3 (all public access blocked,
                      not publicly accessible                pre-signed URLs only)

                      Secrets Manager ── injects UGJCS_DATABASE_URL and UGJCS_JWT_SECRET
                                          as App Runner runtime secrets (never baked
                                          into the image, never in plain env vars)
```

App Runner is the direct replacement for the ECS cluster and services, the ALB, and
CloudFront: it builds/runs the container, terminates TLS on a hostname a browser trusts
out of the box, and health-checks the running instance — the same three jobs those three
services split between them. RDS and the App Runner containers share the default VPC
through an **App Runner VPC connector**, so the database keeps no public route while
needing no NAT gateway, no bespoke two-AZ subnet layout, and no bastion. There is no
Redis and no worker service: nothing in Plans 1–5 has yet produced a background job that
needs one, so provisioning one now would be infrastructure with no caller — the original
plan's own "optional" framing for that module is honoured by deleting it rather than
carrying it unused.

**Tech Stack:** Terraform 1.10.5 (AWS provider ~> 5.0, local state), Docker multi-stage
build, AWS App Runner / ECR / RDS PostgreSQL 16 / S3 / Secrets Manager / IAM, GitHub
Actions (`aws-actions/configure-aws-credentials`, `aws-actions/amazon-ecr-login`), the
`aws` CLI, `gh` CLI, Vercel (frontend, unchanged from Plan 5).

## Global Constraints

- **Task 1 comes first and nothing else in this plan runs before it.** TD-01 in
  `docs/04-technical-debt-register.md` marks root-credential use as Critical and requires
  resolution *before any infrastructure is provisioned*, not merely before real users.
  Every AWS CLI and Terraform command from Task 2 onward runs as `--profile ugjcs-deploy`,
  never as the root profile.
- **Region:** `eu-west-1`. App Runner needs no custom-domain certificate (the requirement
  for a region-specific ACM request only applies to a *custom* domain, which this project
  does not use), so the region is a free choice; `eu-west-1` is used throughout.
- **No bespoke VPC.** Terraform reads the account's **default VPC** and its existing
  subnets via data sources. RDS sits in it with `publicly_accessible = false` and a
  security group that only accepts inbound `5432` from the App Runner VPC connector's
  security group — "not publicly accessible" is enforced at the instance flag and the
  security group both, not by network topology alone.
- **No NAT gateway, no bastion.** The App Runner VPC connector gives App Runner instances
  a private route to RDS without one; RDS needs no route to the internet at all.
- **Terraform state is local**, committed nowhere (`infra/.gitignore` excludes it). A
  remote backend with locking (S3 + DynamoDB) is the correct answer for a team; for one
  operator against a deadline it is scope this plan deliberately does not spend on.
- Conventional Commits. Author: Roger Koranteng Obeng, student ID 22424140.
- Infrastructure cannot be unit-tested. Every task's verification step is a command run
  against the real, live resource, with the expected output stated. "It applied without
  error" is not verification; a command that proves the resource *works* is.
- **Budget reality.** `db.t4g.micro` plus a single App Runner instance (1 vCPU / 2 GB, the
  smallest App Runner offers) plus S3/Secrets Manager/ECR storage runs in the
  low tens of USD/month — smaller than the ECS/ALB/CloudFront footprint it replaces,
  because there is no ALB hourly charge and no CloudFront distribution to pay for.

## Cross-plan dependency — read before starting Task 3

This plan assumes Plan 4 (the editorial API — not present under `backend/src/ugjcs/` at
the time this plan was written; only `domain/`, `application/`, and `infrastructure/`
exist) has produced a FastAPI application importable as `ugjcs.api.main:app`, exposing
`GET /health` → HTTP 200, and authentication endpoints consuming Plan 3's
`IdentityService`. Task 3 (the Dockerfile) and Task 6 (external verification, which logs
in as a seeded test user) cannot be completed without it.

**Do not fabricate a placeholder API here.** If Plan 4 has not landed when this plan is
executed, stop at the start of Task 3, finish Plan 4 first, and resume.

## Interfaces inherited from Plans 1–5

Implementers must not redefine these; import them.

- `ugjcs.infrastructure.config.Settings` — env-prefixed `UGJCS_`; requires
  `UGJCS_DATABASE_URL` (`postgresql+asyncpg://...`) and `UGJCS_JWT_SECRET` with **no
  default value** for either (Plan 2, Plan 3).
- `ugjcs.infrastructure.db.engine.create_engine`, `session_factory` (Plan 2).
- `ugjcs.infrastructure.db.uow.SqlAlchemyUnitOfWork(session_factory)` — `.manuscripts`,
  `.accounts`, `commit()`, `rollback()` (Plan 2; `.accounts` added by Plan 3).
- `ugjcs.domain.account.Account`, `EmailAddress` — `Account(id, email, password_hash,
  full_name, affiliation, expertise=(), reviewer_capacity=3)`; `.grant(role)`,
  `.verify(occurred_at=...)` (Plan 3).
- `ugjcs.domain.enums.Role` — `AUTHOR`, `REVIEWER`, `EDITOR`, `EDITOR_IN_CHIEF`,
  `ADMINISTRATOR` (Plan 1).
- `ugjcs.infrastructure.security.passwords.Argon2PasswordHasher` — `.hash(password) ->
  str` (Plan 3).
- `ugjcs.domain.manuscript.Manuscript`, `ugjcs.domain.ids.TrackingCode.mint(year, seq)`
  (Plan 1); `.submit(actor_id, occurred_at)` (Plan 1, exercised by Plan 2's tests).
- `ugjcs.infrastructure.db.repository.SqlAlchemyManuscriptRepository` (Plan 2).
- Alembic revision history under `backend/alembic/versions/` — this plan runs `alembic
  upgrade head` and never names a specific revision.
- `ugjcs.api.main:app`, `GET /health` — **assumed from Plan 4**, see above.

---

## File Structure

```
infra/
├── providers.tf                                Task 2   terraform + aws + random providers
├── variables.tf                                Task 2   project-wide inputs
├── network.tf                                  Task 2   default VPC + subnet data sources
├── security_groups.tf                          Task 2   rds + apprunner-connector groups
├── ecr.tf                                       Task 2   ECR repository + lifecycle policy
├── s3.tf                                        Task 2   manuscripts bucket, public access blocked
├── secrets.tf                                   Task 2   jwt secret / Task 4 adds database_url secret
├── rds.tf                                       Task 4   RDS PostgreSQL, not publicly accessible
├── iam.tf                                       Task 4   App Runner ECR-access + instance roles
├── apprunner.tf                                 Task 4   VPC connector + App Runner service
├── outputs.tf                                   Task 2, extended Task 4
├── .gitignore                                   Task 2   excludes .terraform/, *.tfstate*
└── ugjcs-deploy-policy.json                     Task 1   IAM policy for the deploy user

backend/
├── Dockerfile                                   Task 3   multi-stage, non-root
├── .dockerignore                                Task 3
├── entrypoint.sh                                Task 3   migrate → seed-if-empty → serve
└── src/ugjcs/scripts/
    ├── __init__.py                              Task 3
    └── seed_demo.py                             Task 3   demo corpus + 5 judge accounts

.github/workflows/
└── deploy.yml                                   Task 5   build, push, deploy, smoke-test

Deployment_and_Source_Links.txt                  Task 5   live URL, credentials, repo link
```

---

### Task 1: Replace root with a scoped IAM deploy user (TD-01)

**Files:**
- Create: `infra/ugjcs-deploy-policy.json`

**Interfaces:**
- Produces: IAM user `ugjcs-deploy`, AWS CLI profile `ugjcs-deploy`, GitHub Actions
  secrets `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`.

**Scope note.** A deploy user that can only run the five named services (App Runner, ECR,
RDS, S3, Secrets Manager) but cannot *provision* them is not a working replacement for
root — Terraform also needs EC2 (to read the default VPC/subnets and manage security
groups), IAM (to create and pass the two roles App Runner needs), and CloudWatch Logs (App
Runner writes there automatically). The policy below scopes what AWS lets be scoped by
resource-name prefix (`ugjcs-*`) and adds an explicit deny block closing the
privilege-escalation paths a broad IAM grant would otherwise open.

- [ ] **Step 1: HUMAN ACTION — enable MFA on the root account, then sign in as root one
  last time**

  This step cannot be scripted: enabling MFA is a console action requiring a physical or
  virtual authenticator device the operator holds. Do this before Step 2; the account
  should never again be used without MFA challenge from this point forward.

- [ ] **Step 2: Write the deploy policy**

Create `infra/ugjcs-deploy-policy.json` (replace `854924711083` if the account changes):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EcrRepoScoped",
      "Effect": "Allow",
      "Action": "ecr:*",
      "Resource": "arn:aws:ecr:eu-west-1:854924711083:repository/ugjcs-*"
    },
    {
      "Sid": "EcrAuthToken",
      "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken",
      "Resource": "*"
    },
    {
      "Sid": "AppRunnerFull",
      "Effect": "Allow",
      "Action": "apprunner:*",
      "Resource": "*"
    },
    {
      "Sid": "RdsScoped",
      "Effect": "Allow",
      "Action": "rds:*",
      "Resource": [
        "arn:aws:rds:eu-west-1:854924711083:db:ugjcs-*",
        "arn:aws:rds:eu-west-1:854924711083:subgrp:ugjcs-*",
        "arn:aws:rds:eu-west-1:854924711083:snapshot:ugjcs-*"
      ]
    },
    {
      "Sid": "RdsDescribe",
      "Effect": "Allow",
      "Action": ["rds:Describe*", "rds:ListTagsForResource"],
      "Resource": "*"
    },
    {
      "Sid": "S3BucketScoped",
      "Effect": "Allow",
      "Action": "s3:*",
      "Resource": ["arn:aws:s3:::ugjcs-*", "arn:aws:s3:::ugjcs-*/*"]
    },
    {
      "Sid": "S3ListAll",
      "Effect": "Allow",
      "Action": "s3:ListAllMyBuckets",
      "Resource": "*"
    },
    {
      "Sid": "SecretsScoped",
      "Effect": "Allow",
      "Action": "secretsmanager:*",
      "Resource": "arn:aws:secretsmanager:eu-west-1:854924711083:secret:ugjcs/*"
    },
    {
      "Sid": "LogsScoped",
      "Effect": "Allow",
      "Action": "logs:*",
      "Resource": [
        "arn:aws:logs:eu-west-1:854924711083:log-group:/aws/apprunner/ugjcs-*",
        "arn:aws:logs:eu-west-1:854924711083:log-group:/aws/apprunner/ugjcs-*:*"
      ]
    },
    {
      "Sid": "LogsDescribe",
      "Effect": "Allow",
      "Action": ["logs:DescribeLogGroups"],
      "Resource": "*"
    },
    {
      "Sid": "Ec2NetworkDescribe",
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeAvailabilityZones",
        "ec2:DescribeNetworkInterfaces"
      ],
      "Resource": "*"
    },
    {
      "Sid": "Ec2SecurityGroupManage",
      "Effect": "Allow",
      "Action": [
        "ec2:CreateSecurityGroup",
        "ec2:DeleteSecurityGroup",
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:AuthorizeSecurityGroupEgress",
        "ec2:RevokeSecurityGroupIngress",
        "ec2:RevokeSecurityGroupEgress",
        "ec2:CreateTags"
      ],
      "Resource": "*"
    },
    {
      "Sid": "IamRoleScoped",
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:DeleteRole",
        "iam:GetRole",
        "iam:PutRolePolicy",
        "iam:DeleteRolePolicy",
        "iam:GetRolePolicy",
        "iam:AttachRolePolicy",
        "iam:DetachRolePolicy",
        "iam:PassRole",
        "iam:TagRole",
        "iam:ListRolePolicies",
        "iam:ListAttachedRolePolicies"
      ],
      "Resource": "arn:aws:iam::854924711083:role/ugjcs-*"
    },
    {
      "Sid": "DenyPrivilegeEscalation",
      "Effect": "Deny",
      "Action": [
        "iam:CreateUser",
        "iam:DeleteUser",
        "iam:CreatePolicy",
        "iam:CreatePolicyVersion",
        "iam:AttachUserPolicy",
        "iam:PutUserPolicy",
        "iam:CreateAccessKey",
        "iam:UpdateAssumeRolePolicy",
        "organizations:*",
        "account:*"
      ],
      "Resource": "*"
    }
  ]
}
```

- [ ] **Step 3: Create the user and attach the policy (as root, one last time)**

```bash
aws iam create-user --user-name ugjcs-deploy
aws iam put-user-policy \
  --user-name ugjcs-deploy \
  --policy-name ugjcs-deploy-policy \
  --policy-document file://infra/ugjcs-deploy-policy.json
aws iam create-access-key --user-name ugjcs-deploy > /tmp/ugjcs-deploy-key.json
cat /tmp/ugjcs-deploy-key.json
```

- [ ] **Step 4: Configure the local CLI profile from the printed key, then shred it**

```bash
aws configure set aws_access_key_id     "<AccessKeyId from Step 3>"     --profile ugjcs-deploy
aws configure set aws_secret_access_key "<SecretAccessKey from Step 3>" --profile ugjcs-deploy
aws configure set region eu-west-1 --profile ugjcs-deploy
shred -u /tmp/ugjcs-deploy-key.json 2>/dev/null || rm -f /tmp/ugjcs-deploy-key.json
```

- [ ] **Step 5: HUMAN ACTION — register the same key pair as GitHub Actions secrets**

```bash
gh secret set AWS_ACCESS_KEY_ID     --repo <owner>/<repo>
gh secret set AWS_SECRET_ACCESS_KEY --repo <owner>/<repo>
```

`gh secret set` is interactive (it prompts for the value, or reads stdin) and requires a
prior `gh auth login` — this cannot be scripted unattended.

- [ ] **Step 6: Verify the profile is not root**

Run:
```bash
aws sts get-caller-identity --profile ugjcs-deploy
```
Expected: `"Arn": "arn:aws:iam::854924711083:user/ugjcs-deploy"` — **not**
`arn:...:root`. If it says root, stop; nothing past this point may run under that profile.

- [ ] **Step 7: HUMAN ACTION — stop using root**

Sign out of the root session used in Step 3. From here on, every AWS action in this plan
uses `--profile ugjcs-deploy` (CLI) or the `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`
secrets (GitHub Actions) — never root.

- [ ] **Step 8: Commit**

```bash
git add infra/ugjcs-deploy-policy.json
git commit -m "chore: replace AWS root credentials with a scoped IAM deploy user (TD-01)"
```

---

### Task 2: Terraform foundation — networking, ECR, S3, Secrets Manager

**Files:**
- Create: `infra/providers.tf`, `infra/variables.tf`, `infra/network.tf`,
  `infra/security_groups.tf`, `infra/ecr.tf`, `infra/s3.tf`, `infra/secrets.tf`,
  `infra/outputs.tf`, `infra/.gitignore`

**Interfaces:**
- Produces: `aws_ecr_repository.backend`, `aws_s3_bucket.manuscripts`,
  `aws_security_group.rds`, `aws_security_group.apprunner_connector`,
  `aws_secretsmanager_secret.jwt_secret`.

- [ ] **Step 1: Providers**

Create `infra/providers.tf`:

```hcl
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

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile

  default_tags {
    tags = {
      project = "ugjcs"
    }
  }
}
```

- [ ] **Step 2: Variables**

Create `infra/variables.tf`:

```hcl
variable "aws_region" {
  type    = string
  default = "eu-west-1"
}

variable "aws_profile" {
  type    = string
  default = "ugjcs-deploy"
}

variable "project_name" {
  type    = string
  default = "ugjcs"
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "db_name" {
  type    = string
  default = "ugjcs"
}

variable "db_username" {
  type    = string
  default = "ugjcs_app"
}
```

- [ ] **Step 3: Default VPC data sources**

Create `infra/network.tf`:

```hcl
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}
```

- [ ] **Step 4: Security groups**

Create `infra/security_groups.tf`:

```hcl
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
```

- [ ] **Step 5: ECR repository**

Create `infra/ecr.tf`:

```hcl
resource "aws_ecr_repository" "backend" {
  name                 = "ugjcs-backend"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "backend" {
  repository = aws_ecr_repository.backend.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Expire untagged images after 7 days"
      selection = {
        tagStatus   = "untagged"
        countType   = "sinceImagePushed"
        countUnit   = "days"
        countNumber = 7
      }
      action = { type = "expire" }
    }]
  })
}
```

- [ ] **Step 6: S3 bucket, all public access blocked**

Create `infra/s3.tf`:

```hcl
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
```

Every document a reviewer or reader retrieves is reached through a pre-signed URL issued
by the application, never a bucket policy grant — that is what "all public access
blocked" buys: even a misconfigured application-layer bug cannot make an object world
readable, because the bucket itself refuses to allow it.

- [ ] **Step 7: Secrets Manager — the JWT key (database_url follows in Task 4, once RDS
  exists)**

Create `infra/secrets.tf`:

```hcl
resource "random_password" "jwt_secret" {
  length  = 64
  special = false
}

resource "aws_secretsmanager_secret" "jwt_secret" {
  name = "ugjcs/jwt-secret"
}

resource "aws_secretsmanager_secret_version" "jwt_secret" {
  secret_id     = aws_secretsmanager_secret.jwt_secret.id
  secret_string = random_password.jwt_secret.result
}
```

- [ ] **Step 8: Outputs and gitignore**

Create `infra/outputs.tf`:

```hcl
output "ecr_repository_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "s3_bucket_name" {
  value = aws_s3_bucket.manuscripts.bucket
}

output "jwt_secret_arn" {
  value = aws_secretsmanager_secret.jwt_secret.arn
}
```

Create `infra/.gitignore`:

```
.terraform/
*.tfstate
*.tfstate.*
.terraform.lock.hcl
crash.log
```

- [ ] **Step 9: Apply and verify**

```bash
cd infra
terraform init
terraform apply -auto-approve
```

Verify:
```bash
aws ecr describe-repositories --repository-names ugjcs-backend --profile ugjcs-deploy --region eu-west-1 --query 'repositories[0].repositoryUri'
aws s3api get-public-access-block --bucket "$(terraform output -raw s3_bucket_name)" --profile ugjcs-deploy --region eu-west-1
```
Expected: the repository URI prints; the public-access-block response shows all four
flags `true`.

- [ ] **Step 10: Commit**

```bash
git add infra/providers.tf infra/variables.tf infra/network.tf infra/security_groups.tf \
        infra/ecr.tf infra/s3.tf infra/secrets.tf infra/outputs.tf infra/.gitignore
git commit -m "feat: provision ECR, S3 and the JWT secret in the default VPC"
```

---

### Task 3: Dockerfile, entrypoint and the seed script

**Files:**
- Create: `backend/Dockerfile`, `backend/.dockerignore`, `backend/entrypoint.sh`,
  `backend/src/ugjcs/scripts/__init__.py`, `backend/src/ugjcs/scripts/seed_demo.py`

**Interfaces:**
- Consumes: `ugjcs.api.main:app` (Plan 4), `ugjcs.infrastructure.db.uow.SqlAlchemyUnitOfWork`,
  `ugjcs.domain.account.Account`, `ugjcs.infrastructure.security.passwords.Argon2PasswordHasher`.
- Produces: a runnable container image; an ECR image tagged `latest` that Task 4's App
  Runner service can be created against (App Runner requires the image to already exist).

- [ ] **Step 1: Write the multi-stage Dockerfile**

Create `backend/Dockerfile`:

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.13-slim AS builder
WORKDIR /app
RUN pip install --no-cache-dir "uv==0.9.*"

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY alembic.ini ./
COPY alembic ./alembic
RUN uv sync --frozen --no-dev

FROM python:3.13-slim AS runtime
RUN addgroup --system app && adduser --system --ingroup app --home /app app
WORKDIR /app

COPY --from=builder --chown=app:app /app /app
COPY --chown=app:app entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

ENV PATH="/app/.venv/bin:${PATH}" PYTHONUNBUFFERED=1
USER app
EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
```

The runtime stage never installs `uv` — only the `.venv` the builder stage produced is
copied across, so the final image carries no build toolchain and runs as `app`, not
`root`.

- [ ] **Step 2: Write the entrypoint**

Create `backend/entrypoint.sh`:

```bash
#!/bin/sh
set -eu

echo "Running Alembic migrations..."
alembic upgrade head

echo "Seeding demo corpus and judge accounts if the database is empty..."
python -m ugjcs.scripts.seed_demo --if-empty

echo "Starting API server..."
exec uvicorn ugjcs.api.main:app --host 0.0.0.0 --port 8000
```

**Why migration and seeding happen here, not in CI.** RDS has `publicly_accessible =
false` and a security group open only to the App Runner VPC connector — a GitHub-hosted
runner has no route to it at all, by design. The App Runner container is the only thing
on this deployment's critical path that both has network access to the database *and*
runs on every deploy, so it is where `alembic upgrade head` and the idempotent seed both
run, before the server starts accepting traffic. Task 5's workflow documents this
explicitly rather than pretending to run migrations from the runner.

- [ ] **Step 3: Write `.dockerignore`**

Create `backend/.dockerignore`:

```
.venv/
__pycache__/
*.pyc
tests/
.git/
.mypy_cache/
.ruff_cache/
.pytest_cache/
.hypothesis/
.import_linter_cache/
.coverage
```

- [ ] **Step 4: Write the seed script**

Create `backend/src/ugjcs/scripts/__init__.py` (empty) and
`backend/src/ugjcs/scripts/seed_demo.py`:

```python
"""Seed a demo corpus and five pre-verified judge accounts.

Idempotent by design: `--if-empty` (the flag the entrypoint always passes) checks for an
existing seeded administrator before writing anything, so re-running this on every
container start — which the entrypoint does — is a cheap no-op after the first boot.

Credentials are intentionally fixed, not generated, and are also written verbatim into
Deployment_and_Source_Links.txt (Task 5): this is an assessment corpus for an examiner to
log into, not a production tenant, so there is nothing to keep secret about them beyond
the AWS account itself.
"""

import argparse
import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from ugjcs.domain.account import Account, EmailAddress
from ugjcs.domain.enums import Role
from ugjcs.domain.ids import TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.infrastructure.config import get_settings
from ugjcs.infrastructure.db.engine import create_engine, session_factory
from ugjcs.infrastructure.db.uow import SqlAlchemyUnitOfWork
from ugjcs.infrastructure.security.passwords import Argon2PasswordHasher

NOW = datetime.now(UTC)
HASHER = Argon2PasswordHasher()

# Fixed, documented credentials for the five judge accounts. Copied verbatim into
# Deployment_and_Source_Links.txt — do not regenerate these per deploy, or the two
# sources of truth drift.
JUDGE_ACCOUNTS: list[tuple[str, str, Role]] = [
    ("author@ugjcs.test", "UgjcsJudge!Author1", Role.AUTHOR),
    ("reviewer@ugjcs.test", "UgjcsJudge!Reviewer1", Role.REVIEWER),
    ("editor@ugjcs.test", "UgjcsJudge!Editor1", Role.EDITOR),
    ("eic@ugjcs.test", "UgjcsJudge!Eic1", Role.EDITOR_IN_CHIEF),
    ("admin@ugjcs.test", "UgjcsJudge!Admin1", Role.ADMINISTRATOR),
]


async def _already_seeded(uow: SqlAlchemyUnitOfWork) -> bool:
    existing = await uow.accounts.get_by_email(EmailAddress("admin@ugjcs.test"))
    return existing is not None


async def _create_accounts(uow: SqlAlchemyUnitOfWork) -> dict[str, UserId]:
    ids: dict[str, UserId] = {}
    for email, password, role in JUDGE_ACCOUNTS:
        account = Account(
            id=UserId(uuid4()),
            email=EmailAddress(email),
            password_hash=HASHER.hash(password),
            full_name=email.split("@")[0].replace(".", " ").title(),
            affiliation="University of Ghana",
        )
        account.grant(role)
        account.verify(occurred_at=NOW)
        await uow.accounts.add(account)
        ids[email] = account.id
    return ids


async def _create_demo_corpus(uow: SqlAlchemyUnitOfWork, author_id: UserId) -> None:
    titles = [
        "Sparse Retrieval for Low-Resource Languages",
        "Fair Scheduling for Shared GPU Clusters",
        "Edge Caching for Campus Networks",
    ]
    for sequence, title in enumerate(titles, start=1):
        manuscript = Manuscript(
            id=uuid4(),  # type: ignore[arg-type]
            tracking_code=TrackingCode.mint(NOW.year, sequence),
            title=title,
            abstract=f"A demonstration submission seeded for assessment: {title}.",
            keywords=("demo",),
            author_ids=(author_id,),
            corresponding_author_id=author_id,
        )
        manuscript.submit(actor_id=author_id, occurred_at=NOW)
        await uow.manuscripts.add(manuscript)


async def run(*, only_if_empty: bool) -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url, echo=False)
    factory = session_factory(engine)
    async with SqlAlchemyUnitOfWork(factory) as uow:
        if only_if_empty and await _already_seeded(uow):
            print("Demo data already present; skipping.")
            return
        ids = await _create_accounts(uow)
        await _create_demo_corpus(uow, author_id=ids["author@ugjcs.test"])
        await uow.commit()
        print(f"Seeded {len(JUDGE_ACCOUNTS)} judge accounts and {3} demo manuscripts.")
    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--if-empty", action="store_true", default=False)
    args = parser.parse_args()
    asyncio.run(run(only_if_empty=args.if_empty))


if __name__ == "__main__":
    main()
```

If Plan 3's `AccountRepository` names `get_by_email` differently, use the name Plan 3
actually produced — this script must not redefine that port, only call it.

- [ ] **Step 5: Build and push a bootstrap image**

App Runner (Task 4) requires the ECR image to exist *before* the service resource can be
created — there is no chicken-and-egg option in Terraform for this. Push one now:

```bash
cd backend
aws ecr get-login-password --profile ugjcs-deploy --region eu-west-1 \
  | docker login --username AWS --password-stdin 854924711083.dkr.ecr.eu-west-1.amazonaws.com

docker build -t ugjcs-backend:bootstrap .
docker tag ugjcs-backend:bootstrap 854924711083.dkr.ecr.eu-west-1.amazonaws.com/ugjcs-backend:latest
docker push 854924711083.dkr.ecr.eu-west-1.amazonaws.com/ugjcs-backend:latest
```

Verify:
```bash
aws ecr describe-images --repository-name ugjcs-backend --profile ugjcs-deploy --region eu-west-1 \
  --query 'imageDetails[*].imageTags'
```
Expected: `[["latest"]]`.

- [ ] **Step 6: Run the gates and commit**

Run: `cd backend && make check`, then:

```bash
git add backend/Dockerfile backend/.dockerignore backend/entrypoint.sh backend/src/ugjcs/scripts
git commit -m "feat: add a non-root multi-stage Dockerfile and the demo seed script"
```

---

### Task 4: Terraform — RDS, VPC connector and the App Runner service

**Files:**
- Create: `infra/rds.tf`, `infra/iam.tf`, `infra/apprunner.tf`
- Modify: `infra/secrets.tf`, `infra/outputs.tf`

**Interfaces:**
- Produces: `aws_db_instance.postgres` (not publicly accessible),
  `aws_apprunner_vpc_connector.connector`, `aws_apprunner_service.api`, output
  `apprunner_service_url`.

- [ ] **Step 1: RDS, private**

Create `infra/rds.tf`:

```hcl
resource "aws_db_subnet_group" "postgres" {
  name       = "ugjcs-db-subnet-group"
  subnet_ids = data.aws_subnets.default.ids
}

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

  # This, together with the security group in Task 2, is what "not publicly accessible"
  # means: no public IP is assigned, AND only the App Runner connector's security group
  # may reach port 5432.
  publicly_accessible = false

  multi_az                = false
  backup_retention_period = 1
  skip_final_snapshot     = true
  deletion_protection     = false
  apply_immediately       = true
}
```

`db.t4g.micro` is the smallest Graviton-based burstable class RDS offers for PostgreSQL —
appropriate for a demo corpus of a few manuscripts and five accounts, not for production
load.

- [ ] **Step 2: The database_url secret, now that the endpoint exists**

Add to `infra/secrets.tf`:

```hcl
resource "aws_secretsmanager_secret" "database_url" {
  name = "ugjcs/database-url"
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id = aws_secretsmanager_secret.database_url.id
  secret_string = "postgresql+asyncpg://${var.db_username}:${random_password.db_password.result}@${aws_db_instance.postgres.endpoint}/${var.db_name}"
}
```

- [ ] **Step 3: IAM roles App Runner needs**

Create `infra/iam.tf`:

```hcl
# Lets App Runner's build service pull the private image from ECR.
data "aws_iam_policy_document" "apprunner_build_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["build.apprunner.com"]
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
      identifiers = ["tasks.apprunner.com"]
    }
  }
}

resource "aws_iam_role" "apprunner_instance" {
  name               = "ugjcs-apprunner-instance"
  assume_role_policy = data.aws_iam_policy_document.apprunner_instance_trust.json
}

data "aws_iam_policy_document" "apprunner_instance_permissions" {
  statement {
    sid       = "ReadRuntimeSecrets"
    actions   = ["secretsmanager:GetSecretValue"]
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
```

- [ ] **Step 4: VPC connector and the App Runner service**

Create `infra/apprunner.tf`:

```hcl
resource "aws_apprunner_vpc_connector" "connector" {
  vpc_connector_name = "ugjcs-connector"
  subnets             = data.aws_subnets.default.ids
  security_groups     = [aws_security_group.apprunner_connector.id]
}

resource "aws_apprunner_service" "api" {
  service_name = "ugjcs-backend"

  source_configuration {
    auto_deployments_enabled = false # Task 5's workflow triggers deployments explicitly

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
    cpu               = "1024"
    memory            = "2048"
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
```

`egress_type = "VPC"` is what routes the container's outbound traffic to RDS through the
connector instead of the public internet — this one setting is doing the job the ECS
task's subnet placement and security group did in the design this replaces.

- [ ] **Step 5: Extend outputs**

Add to `infra/outputs.tf`:

```hcl
output "apprunner_service_url" {
  value = "https://${aws_apprunner_service.api.service_url}"
}

output "apprunner_service_arn" {
  value = aws_apprunner_service.api.arn
}

output "rds_endpoint" {
  value     = aws_db_instance.postgres.endpoint
  sensitive = true
}
```

- [ ] **Step 6: Apply and verify**

```bash
cd infra
terraform apply -auto-approve
```

RDS provisioning alone typically takes 5–10 minutes; App Runner's first deployment
another 2–5. Verify both:

```bash
aws rds describe-db-instances --db-instance-identifier ugjcs-postgres \
  --profile ugjcs-deploy --region eu-west-1 --query 'DBInstances[0].[DBInstanceStatus,PubliclyAccessible]'
# Expected: ["available", false]

aws apprunner describe-service \
  --service-arn "$(terraform output -raw apprunner_service_arn)" \
  --profile ugjcs-deploy --region eu-west-1 --query 'Service.Status'
# Expected: "RUNNING"

curl -sS -o /dev/null -w '%{http_code}\n' "$(terraform output -raw apprunner_service_url)/health"
# Expected: 200
```

- [ ] **Step 7: Commit**

```bash
git add infra/rds.tf infra/iam.tf infra/apprunner.tf infra/secrets.tf infra/outputs.tf
git commit -m "feat: provision private RDS and an App Runner service behind a VPC connector"
```

---

### Task 5: Deploy workflow, seeded credentials, and the source-links document

**Files:**
- Create: `.github/workflows/deploy.yml`, `Deployment_and_Source_Links.txt`

**Interfaces:**
- Consumes: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (Task 1); `apprunner_service_arn`
  output (Task 4).
- Produces: GitHub Actions secret `APPRUNNER_SERVICE_ARN`; a populated
  `Deployment_and_Source_Links.txt` at the repository root.

- [ ] **Step 1: Register the service ARN as a secret (HUMAN ACTION — interactive)**

```bash
cd infra
gh secret set APPRUNNER_SERVICE_ARN --repo <owner>/<repo> --body "$(terraform output -raw apprunner_service_arn)"
```

- [ ] **Step 2: Write the workflow**

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy backend

on:
  push:
    branches: [main]
    paths: ["backend/**"]
  workflow_dispatch: {}

env:
  AWS_REGION: eu-west-1
  ECR_REPOSITORY: ugjcs-backend

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - id: ecr-login
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and push image
        working-directory: backend
        run: |
          IMAGE="${{ steps.ecr-login.outputs.registry }}/${{ env.ECR_REPOSITORY }}"
          docker build -t "$IMAGE:${{ github.sha }}" -t "$IMAGE:latest" .
          docker push "$IMAGE:${{ github.sha }}"
          docker push "$IMAGE:latest"

      - name: Migrations run inside the new container, not here
        run: |
          echo "RDS has publicly_accessible = false and a security group open only to"
          echo "the App Runner VPC connector, so this GitHub-hosted runner has no route"
          echo "to it. 'alembic upgrade head' runs from backend/entrypoint.sh when the"
          echo "App Runner instance below boots, which is the only place on this path"
          echo "that both reaches the database and runs on every deploy."

      - name: Trigger App Runner deployment
        run: |
          aws apprunner start-deployment --service-arn "${{ secrets.APPRUNNER_SERVICE_ARN }}"

      - name: Wait for the deployment to finish
        run: |
          for i in $(seq 1 30); do
            STATUS=$(aws apprunner describe-service \
              --service-arn "${{ secrets.APPRUNNER_SERVICE_ARN }}" \
              --query 'Service.Status' --output text)
            echo "Status: $STATUS"
            if [ "$STATUS" = "RUNNING" ]; then exit 0; fi
            if [ "$STATUS" = "CREATE_FAILED" ]; then exit 1; fi
            sleep 20
          done
          echo "Timed out waiting for RUNNING"
          exit 1

      - name: Smoke-test the live health endpoint
        run: |
          URL=$(aws apprunner describe-service \
            --service-arn "${{ secrets.APPRUNNER_SERVICE_ARN }}" \
            --query 'Service.ServiceUrl' --output text)
          curl --fail --silent --show-error "https://$URL/health"
```

- [ ] **Step 3: Run it once and verify**

```bash
gh workflow run deploy.yml --repo <owner>/<repo>
gh run watch --repo <owner>/<repo>
```
Expected: all steps green, ending with the smoke-test step printing the `/health`
response body and exiting 0.

- [ ] **Step 4: Write the source-links document**

Create `Deployment_and_Source_Links.txt` at the repository root:

```
UGJCS — Deployment and Source Links
=====================================

Live application
----------------
Frontend (Vercel):        https://<fill in after `vercel --prod`>
Backend (AWS App Runner):  <fill in with `terraform output apprunner_service_url`>
Backend health check:      <backend URL above>/health
API docs:                  <backend URL above>/docs

Source
------
Repository:  https://github.com/<owner>/<repo>
Infrastructure as code:  infra/ (Terraform)
Deployment plan:  docs/superpowers/plans/2026-08-12-ugjcs-plan-6-deployment.md
Technical debt register:  docs/04-technical-debt-register.md

Judge accounts (pre-verified, one per role)
--------------------------------------------
Author            author@ugjcs.test     UgjcsJudge!Author1
Reviewer          reviewer@ugjcs.test   UgjcsJudge!Reviewer1
Editor            editor@ugjcs.test     UgjcsJudge!Editor1
Editor-in-chief   eic@ugjcs.test        UgjcsJudge!Eic1
Administrator     admin@ugjcs.test      UgjcsJudge!Admin1

These accounts and a small demo manuscript corpus (3 submissions) are created
automatically on first container boot by backend/src/ugjcs/scripts/seed_demo.py
(idempotent — safe to re-deploy).

Notes for the assessor
-----------------------
- The backend is fronted by AWS App Runner, which terminates TLS on the
  *.awsapprunner.com hostname above without a registered domain. This is a
  deliberate, documented substitution for the ECS/ALB/CloudFront design in
  the specification's §7.3 — see the deployment plan's "Why this is smaller
  than the specification" section and TD-14 in the technical debt register.
- Do not run `terraform destroy` in infra/ before the viva.
```

- [ ] **Step 5: HUMAN ACTION — point Vercel at the live backend and fill in the URLs**

The frontend's backend base URL must be updated to the App Runner URL, and the file above
completed with both live URLs. This requires an authenticated Vercel session:

```bash
vercel login              # interactive
cd frontend
vercel env add BACKEND_API_URL production   # paste the apprunner_service_url output
vercel --prod
```

Then replace the two `<fill in ...>` placeholders in `Deployment_and_Source_Links.txt`
with the real URLs `vercel --prod` and `terraform output apprunner_service_url` printed.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/deploy.yml Deployment_and_Source_Links.txt
git commit -m "feat: add the App Runner deploy workflow and judge credentials"
```

---

### Task 6: External verification, then teardown

**Files:** none (verification and infrastructure destruction only).

**Interfaces:**
- Consumes: `apprunner_service_url` output, the five judge accounts from Task 5.

- [ ] **Step 1: Curl the App Runner URL over HTTPS from outside AWS**

```bash
cd infra
URL="$(terraform output -raw apprunner_service_url)"
curl -sS -o /dev/null -w '%{http_code}\n' "$URL/health"
```
Expected: `200`. A non-200 or a TLS error here means Task 4's health check
configuration or the container's `/health` route is broken — stop and fix before
continuing.

- [ ] **Step 2: Log in as a seeded judge and confirm a token comes back**

```bash
curl -sS -X POST "$URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"eic@ugjcs.test","password":"UgjcsJudge!Eic1"}'
```
Expected: HTTP 200 with a JSON body containing an `access_token` field. A 401 means the
seed script did not run or the password hash does not match — check the App Runner
service logs:
```bash
aws logs tail /aws/apprunner/ugjcs-backend/service --profile ugjcs-deploy --region eu-west-1 --since 1h
```

- [ ] **Step 3: Confirm the Vercel frontend reaches the backend**

```bash
FRONTEND_URL="<the frontend URL from Deployment_and_Source_Links.txt>"
curl -sS -o /dev/null -w '%{http_code}\n' "$FRONTEND_URL"
```
Expected: `200`. Then, in a browser, open `$FRONTEND_URL`, log in as
`eic@ugjcs.test` / `UgjcsJudge!Eic1`, and confirm the editorial dashboard loads with the
three seeded demo manuscripts visible — this is the end-to-end proof that the Vercel BFF
successfully proxies to the App Runner backend over HTTPS with no CORS or cookie failure.

- [ ] **Step 4: Record the result**

If Steps 1–3 all pass, the deployment is verified end-to-end from outside AWS and Vercel
both. Note the verification date and the three response codes observed in
`Deployment_and_Source_Links.txt` under a `Verified:` line.

---

- [ ] **Step 5: Teardown — WARNING: DO NOT RUN THIS BEFORE THE VIVA**

Running the commands below deletes the live App Runner service, the RDS instance, the S3
bucket contents, and every secret — the URL in `Deployment_and_Source_Links.txt` stops
answering within minutes and cannot be brought back with the same hostname. Run this only
after the assessment is complete, or when re-provisioning for a fresh demo.

```bash
cd infra
terraform destroy
# Terraform lists every resource it will delete and asks for "yes" — read it before typing.
```

Verify teardown completed:
```bash
aws apprunner list-services --profile ugjcs-deploy --region eu-west-1 --query 'ServiceSummaryList'
# Expected: []

aws rds describe-db-instances --profile ugjcs-deploy --region eu-west-1 \
  --query "DBInstances[?DBInstanceIdentifier=='ugjcs-postgres']"
# Expected: []
```

Optional, only after grading is finalised: delete the `ugjcs-deploy` IAM user and its
access key, and the `ugjcs-backend` ECR repository's stored images, to leave the AWS
account with no standing footprint for this project at all.
