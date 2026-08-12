# UGJCS Plan 6 — Deployment and Infrastructure

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the backend and frontend built by Plans 1–5 into a live application an examiner can open over HTTPS, with admin and test credentials that work, on infrastructure provisioned by a scoped IAM principal rather than the AWS root account. Deployment is 3 of 50 marks and is currently zero; this plan is what earns it.

**Architecture:**

```
Reader ─▶ Vercel (Next.js) ─┬─▶ CloudFront ─▶ ALB ─▶ ECS Fargate: api ─┬─▶ RDS Postgres
                            │                                          ├─▶ S3 (private)
                            └── (public pages, cached)                 └─▶ [Redis ─▶ ECS Fargate: worker]  (optional, Task 9)
```

CloudFront is architecturally necessary, not decoration: it is what supplies a trusted TLS
certificate on a `*.cloudfront.net` hostname, which is what lets an HTTPS frontend
(`*.vercel.app`) reach the backend without a registered domain and without hand-rolling a
certificate. The ALB has no certificate of its own and is not meant to be addressed
directly — CloudFront is the only supported entry point to the API. RDS (and Redis, if
Task 9 is applied) sit in private subnets with no route to the internet. ECS Fargate tasks
run in the **public** subnets with security groups that only accept traffic from the ALB;
this is a deliberate cost decision — see "Why no NAT gateway" below.

**Tech Stack:** Terraform 1.10.5 (AWS provider ~> 5.0, local state), Docker multi-stage
build, AWS ECR / ECS Fargate / ALB / CloudFront / RDS PostgreSQL 16 / S3 / Secrets Manager,
GitHub Actions (`aws-actions/configure-aws-credentials`, `aws-actions/amazon-ecr-login`),
Vercel CLI, `gh` CLI.

## Global Constraints

- **Task 1 comes first and nothing else in this plan runs before it.** TD-01 in
  `docs/04-technical-debt-register.md` marks root-credential use as Critical and requires
  resolution *before any infrastructure is provisioned*, not merely before real users.
  Every AWS CLI and Terraform command from Task 2 onward runs as `--profile ugjcs-deploy`,
  never as the root profile.
- **Why no NAT gateway.** The user has accepted roughly USD 35–55/month. A single NAT
  gateway alone runs close to USD 32/month plus data processing, which would consume most
  of that budget on its own. ECS Fargate tasks are therefore placed in the public subnets
  with `assign_public_ip = true` so they can reach ECR, Secrets Manager and the internet
  directly through the Internet Gateway; a security group restricts inbound traffic to
  the ALB only. RDS and (optionally) Redis stay in the private subnets — "private" here
  means no route to the internet, not unreachable from the VPC — and are reached over the
  VPC's internal routing, which needs no NAT.
- **Terraform state is local**, committed nowhere (`infra/.gitignore` excludes it). A
  remote backend with locking (S3 + DynamoDB) is the correct answer for a team; for one
  operator against a 48-hour deadline it is scope this plan deliberately does not spend
  on. Documented, not forgotten.
- **Region:** `eu-west-1`. CloudFront's default certificate needs no region-specific ACM
  request (that requirement only applies to a *custom* domain's certificate, which this
  project does not use), so the backend region is a free choice; `eu-west-1` is used
  throughout every example below.
- Conventional Commits. Author: Roger Koranteng Obeng, student ID 22424140.
- Infrastructure cannot be unit-tested. Every task's verification step is a command run
  against the real, live resource, with the expected output stated. "It applied without
  error" is not verification; a command that proves the resource *works* is.

## Cross-plan dependency — read before starting Task 5

This plan assumes Plan 4 (the editorial API, not yet observed on disk at the time this
plan was written) has produced a FastAPI application importable as `ugjcs.api.main:app`,
exposing `GET /health` → HTTP 200, and authentication endpoints consuming Plan 3's
`IdentityService` (a login endpoint that accepts an email/password pair and returns a
token, per Plan 3's `TokenService` design). Task 5 (the Dockerfile) and Task 9 (external
verification, which logs in as a seeded test user) cannot be completed without it.

**Do not fabricate a placeholder API here.** If Plan 4 has not landed when this plan is
executed, stop at the start of Task 5, finish Plan 4 first, and resume — inventing a stub
`/health` route in this plan would diverge from whatever lifespan wiring, middleware and
dependency injection Plan 4 actually builds, and Task 9's login check would be verifying
against code this plan has no authority to write.

## Interfaces inherited from Plans 1–5

Implementers must not redefine these; import them.

- `ugjcs.infrastructure.config.Settings` — env-prefixed `UGJCS_`; requires
  `UGJCS_DATABASE_URL` (`postgresql+asyncpg://...`) and `UGJCS_JWT_SECRET` with **no
  default value** for either (Plan 2, Plan 3).
- `ugjcs.infrastructure.db.engine.create_engine`, `session_factory` (Plan 2).
- `ugjcs.infrastructure.db.uow.SqlAlchemyUnitOfWork(session_factory)` — `.manuscripts`,
  `.accounts`, `commit()`, `rollback()` (Plan 2; `.accounts` added by Plan 3).
- `ugjcs.domain.account.Account`, `EmailAddress`, `AccountError` — `Account(id, email,
  password_hash, full_name, affiliation, expertise=(), reviewer_capacity=3)`; `.grant(role)`,
  `.verify(occurred_at=...)` (Plan 3).
- `ugjcs.domain.enums.Role` — `AUTHOR`, `REVIEWER`, `EDITOR`, `EDITOR_IN_CHIEF`,
  `ADMINISTRATOR` (Plan 1).
- `ugjcs.infrastructure.security.passwords.Argon2PasswordHasher` — `.hash(password) ->
  str` (Plan 3).
- `ugjcs.domain.manuscript.Manuscript`, `ugjcs.domain.ids.TrackingCode.mint(year, seq)`
  (Plan 1); `.submit(actor_id, occurred_at)`, `.begin_screening(actor_id, occurred_at)`
  (Plan 1, exercised by Plan 2's tests).
- Alembic revision history under `backend/alembic/versions/` — this plan runs `alembic
  upgrade head` and never names a specific revision, so it stays correct regardless of how
  many migrations Plans 3 and 4 have added by the time this plan executes.
- `ugjcs.api.main:app`, `GET /health` — **assumed from Plan 4**, see above.

---

## File Structure

```
infra/
├── providers.tf                                Task 2   terraform + aws + random providers
├── variables.tf                                Task 2   project-wide inputs
├── networking.tf                                Task 2   VPC, 2 public + 2 private subnets, IGW, routes
├── security_groups.tf                          Task 2   alb / ecs / rds security groups
├── ecr.tf                                       Task 2   ECR repository + lifecycle policy
├── s3.tf                                        Task 2   manuscripts bucket, public access blocked
├── secrets.tf                                   Task 2   Secrets Manager scaffolding + random values
├── rds.tf                                       Task 3   RDS PostgreSQL 16, db subnet group
├── alb.tf                                       Task 3   ALB, target group, HTTP listener
├── iam.tf                                       Task 4   ECS execution + task roles
├── ecs.tf                                       Task 4   cluster, task definition, service, log group
├── cloudfront.tf                                Task 4   distribution fronting the ALB
├── outputs.tf                                   Task 2   extended in Tasks 3–4
├── .gitignore                                   Task 2   excludes .terraform/, *.tfstate*
├── ugjcs-deploy-policy.json                     Task 1   IAM policy for the deploy user
└── optional-worker/                             Task 9   SEPARATE state; not applied by default
    ├── providers.tf
    ├── variables.tf
    ├── redis.tf                                          ElastiCache Redis, private subnets
    ├── worker.tf                                          ECS task definition + service for `worker`
    └── outputs.tf

backend/
├── Dockerfile                                   Task 5   multi-stage, non-root
├── .dockerignore                                Task 5
└── scripts/
    └── seed_demo.py                             Task 8   demonstration corpus + judge accounts

.github/workflows/
└── deploy.yml                                   Task 6   build, push, migrate, deploy, smoke-test, rollback

Deployment_and_Source_Links.txt                  Task 8   live URL, credentials, repo link
```

---

### Task 1: Replace root with a scoped IAM deploy user (TD-01)

**Files:**
- Create: `infra/ugjcs-deploy-policy.json`

**Interfaces:**
- Produces: IAM user `ugjcs-deploy`, AWS CLI profile `ugjcs-deploy`, GitHub Actions secrets
  `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`.

**Scope note.** TD-01's resolution text names ECR, ECS, RDS, S3 and CloudFront. Terraform,
however, is the tool provisioning those resources in the first place, and doing that
requires EC2 (VPC/subnet/security-group), ElasticLoadBalancing (the ALB), IAM (creating and
passing the two roles ECS needs), Secrets Manager and CloudWatch Logs as well — a policy
that can deploy but cannot provision is not a working replacement for root. The policy below
grants the named services broadly (scoped by resource-name prefix `ugjcs-*` wherever AWS
supports resource-level permissions) and grants the provisioning-only services (EC2, ELB,
IAM, Secrets Manager) the minimum needed to create and manage this project's resources,
with an explicit deny block closing the privilege-escalation paths a broad IAM grant would
otherwise open.

- [ ] **Step 1: Write the policy**

Create `infra/ugjcs-deploy-policy.json` (replace `854924711083` only if the account
changes):

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
      "Sid": "EcsFull",
      "Effect": "Allow",
      "Action": "ecs:*",
      "Resource": "*",
      "Condition": {
        "StringEquals": { "aws:ResourceTag/project": "ugjcs" }
      }
    },
    {
      "Sid": "EcsRegisterAndRunNoResourceLevelPerms",
      "Effect": "Allow",
      "Action": [
        "ecs:RegisterTaskDefinition",
        "ecs:DeregisterTaskDefinition",
        "ecs:DescribeTaskDefinition",
        "ecs:ListTaskDefinitions",
        "ecs:RunTask",
        "ecs:DescribeTasks",
        "ecs:DescribeClusters",
        "ecs:DescribeServices",
        "ecs:ListClusters"
      ],
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
      "Action": ["rds:Describe*"],
      "Resource": "*"
    },
    {
      "Sid": "S3Scoped",
      "Effect": "Allow",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::ugjcs-*",
        "arn:aws:s3:::ugjcs-*/*"
      ]
    },
    {
      "Sid": "CloudFrontFull",
      "Effect": "Allow",
      "Action": "cloudfront:*",
      "Resource": "*"
    },
    {
      "Sid": "CloudWatchLogsAndMetricsScoped",
      "Effect": "Allow",
      "Action": ["logs:*", "cloudwatch:*"],
      "Resource": "*"
    },
    {
      "Sid": "Ec2NetworkingProvisioning",
      "Effect": "Allow",
      "Action": [
        "ec2:Describe*",
        "ec2:CreateVpc", "ec2:DeleteVpc", "ec2:ModifyVpcAttribute",
        "ec2:CreateSubnet", "ec2:DeleteSubnet", "ec2:ModifySubnetAttribute",
        "ec2:CreateInternetGateway", "ec2:DeleteInternetGateway",
        "ec2:AttachInternetGateway", "ec2:DetachInternetGateway",
        "ec2:CreateRouteTable", "ec2:DeleteRouteTable", "ec2:CreateRoute",
        "ec2:DeleteRoute", "ec2:AssociateRouteTable", "ec2:DisassociateRouteTable",
        "ec2:CreateSecurityGroup", "ec2:DeleteSecurityGroup",
        "ec2:AuthorizeSecurityGroupIngress", "ec2:AuthorizeSecurityGroupEgress",
        "ec2:RevokeSecurityGroupIngress", "ec2:RevokeSecurityGroupEgress",
        "ec2:CreateTags", "ec2:DeleteTags"
      ],
      "Resource": "*"
    },
    {
      "Sid": "LoadBalancing",
      "Effect": "Allow",
      "Action": "elasticloadbalancing:*",
      "Resource": "*"
    },
    {
      "Sid": "SecretsManagerScoped",
      "Effect": "Allow",
      "Action": "secretsmanager:*",
      "Resource": "arn:aws:secretsmanager:eu-west-1:854924711083:secret:ugjcs/*"
    },
    {
      "Sid": "IamRolesForEcsOnly",
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole", "iam:DeleteRole", "iam:GetRole",
        "iam:PutRolePolicy", "iam:DeleteRolePolicy", "iam:GetRolePolicy",
        "iam:AttachRolePolicy", "iam:DetachRolePolicy",
        "iam:ListRolePolicies", "iam:ListAttachedRolePolicies", "iam:TagRole"
      ],
      "Resource": [
        "arn:aws:iam::854924711083:role/ugjcs-ecs-execution-role",
        "arn:aws:iam::854924711083:role/ugjcs-ecs-task-role"
      ]
    },
    {
      "Sid": "IamPassRoleToEcsOnly",
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": [
        "arn:aws:iam::854924711083:role/ugjcs-ecs-execution-role",
        "arn:aws:iam::854924711083:role/ugjcs-ecs-task-role"
      ],
      "Condition": {
        "StringEquals": { "iam:PassedToService": "ecs-tasks.amazonaws.com" }
      }
    },
    {
      "Sid": "ElastiCacheOptional",
      "Effect": "Allow",
      "Action": "elasticache:*",
      "Resource": "*"
    },
    {
      "Sid": "DenyPrivilegeEscalation",
      "Effect": "Deny",
      "Action": [
        "iam:CreateUser", "iam:DeleteUser", "iam:CreateAccessKey",
        "iam:AttachUserPolicy", "iam:PutUserPolicy", "iam:CreateLoginProfile",
        "iam:UpdateLoginProfile", "iam:CreatePolicyVersion",
        "iam:PassRole", "iam:CreateRole"
      ],
      "NotResource": [
        "arn:aws:iam::854924711083:role/ugjcs-ecs-execution-role",
        "arn:aws:iam::854924711083:role/ugjcs-ecs-task-role"
      ]
    },
    {
      "Sid": "DenyAccountLevelActions",
      "Effect": "Deny",
      "Action": ["organizations:*", "account:*", "iam:DeleteAccountPasswordPolicy"],
      "Resource": "*"
    }
  ]
}
```

- [ ] **Step 2: Create the user and attach the policy — as root, one time only**

```bash
aws iam create-user --user-name ugjcs-deploy
aws iam put-user-policy --user-name ugjcs-deploy \
  --policy-name ugjcs-deploy-scoped \
  --policy-document file://infra/ugjcs-deploy-policy.json
aws iam create-access-key --user-name ugjcs-deploy > /tmp/ugjcs-deploy-key.json
cat /tmp/ugjcs-deploy-key.json
```

Expected: JSON containing `AccessKeyId` and `SecretAccessKey`.

- [ ] **Step 3: Configure a named profile and stop using root**

```bash
aws configure set aws_access_key_id "$(jq -r .AccessKey.AccessKeyId /tmp/ugjcs-deploy-key.json)" --profile ugjcs-deploy
aws configure set aws_secret_access_key "$(jq -r .AccessKey.SecretAccessKey /tmp/ugjcs-deploy-key.json)" --profile ugjcs-deploy
aws configure set region eu-west-1 --profile ugjcs-deploy
export AWS_PROFILE=ugjcs-deploy   # for the remainder of this plan, in this shell
rm /tmp/ugjcs-deploy-key.json
```

- [ ] **Step 4: Verify the deploy user is not root, and can act**

```bash
aws sts get-caller-identity --profile ugjcs-deploy
aws ecr describe-repositories --profile ugjcs-deploy 2>&1 | head -5
```

Expected: first command's `Arn` ends in `user/ugjcs-deploy`, **not** `:root`. Second
command returns `RepositoryNotFoundException` or an empty list — a permission error here
(`AccessDenied` on `ecr:DescribeRepositories`) means the policy did not attach; a
`RepositoryNotFoundException` or empty result means the call was authorised and simply
found nothing yet.

- [ ] **Step 5: Store credentials as GitHub Actions secrets**

```bash
gh secret set AWS_ACCESS_KEY_ID --repo rogerkorantenng/ugjcs \
  --body "$(aws configure get aws_access_key_id --profile ugjcs-deploy)"
gh secret set AWS_SECRET_ACCESS_KEY --repo rogerkorantenng/ugjcs \
  --body "$(aws configure get aws_secret_access_key --profile ugjcs-deploy)"
gh secret list --repo rogerkorantenng/ugjcs
```

Expected: `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` listed.

- [ ] **Step 6: Human action — enable MFA on the root user**

**This step cannot be scripted or delegated.** In the AWS Console, as root:
IAM → Security credentials → Assign MFA device. Do this now, while root credentials are
still fresh in mind, and do not use the root profile again for the rest of this plan.
Report back once done; this plan does not proceed to prove it, because it cannot.

- [ ] **Step 7: Commit**

```bash
git add infra/ugjcs-deploy-policy.json
git commit -m "chore: add scoped IAM deploy user policy, resolving TD-01"
```

Do **not** commit the access key. It is already in GitHub secrets and nowhere else.

---

### Task 2: Terraform — networking, security groups, ECR, S3, secrets scaffolding

**Files:**
- Create: `infra/providers.tf`, `infra/variables.tf`, `infra/networking.tf`,
  `infra/security_groups.tf`, `infra/ecr.tf`, `infra/s3.tf`, `infra/secrets.tf`,
  `infra/outputs.tf`, `infra/.gitignore`

**Interfaces:**
- Produces: VPC, 2 public + 2 private subnets across two AZs, three security groups, an ECR
  repository, a private S3 bucket, and two Secrets Manager secrets (values populated fully
  in Task 3).

- [ ] **Step 1: `.gitignore` and providers**

Create `infra/.gitignore`:

```gitignore
.terraform/
.terraform.lock.hcl
*.tfstate
*.tfstate.*
*.tfvars
crash.log
```

Create `infra/providers.tf`:

```hcl
terraform {
  required_version = ">= 1.10.5"
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
  # Local state, deliberately: one operator, one 48-hour window. A remote backend with
  # locking is the right call for a team; it is not the right call here.
}

provider "aws" {
  region  = var.aws_region
  profile = "ugjcs-deploy"

  default_tags {
    tags = {
      project     = "ugjcs"
      environment = "assessment"
      managed_by  = "terraform"
    }
  }
}

data "aws_caller_identity" "current" {}
```

- [ ] **Step 2: Variables**

Create `infra/variables.tf`:

```hcl
variable "aws_region" {
  default = "eu-west-1"
}

variable "project_name" {
  default = "ugjcs"
}

variable "vpc_cidr" {
  default = "10.0.0.0/16"
}

variable "azs" {
  default = ["eu-west-1a", "eu-west-1b"]
}

variable "public_subnet_cidrs" {
  default = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  default = ["10.0.11.0/24", "10.0.12.0/24"]
}

variable "container_port" {
  default = 8000
}

variable "health_check_path" {
  default = "/health"
}

variable "db_instance_class" {
  default = "db.t4g.micro"
}

variable "db_name" {
  default = "ugjcs"
}

variable "db_username" {
  default = "ugjcs_app"
}

variable "task_cpu" {
  default = "256"
}

variable "task_memory" {
  default = "512"
}

variable "desired_count" {
  default = 1
}
```

- [ ] **Step 3: Networking**

Create `infra/networking.tf`:

```hcl
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = "${var.project_name}-vpc" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${var.project_name}-igw" }
}

resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = var.azs[count.index]
  map_public_ip_on_launch = true
  tags                    = { Name = "${var.project_name}-public-${var.azs[count.index]}" }
}

# "Private" means no route to the internet — RDS and (optionally) Redis live here. It does
# not mean unreachable: resources in the public subnets reach these over the VPC's local
# route, which needs no NAT gateway.
resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = var.azs[count.index]
  tags              = { Name = "${var.project_name}-private-${var.azs[count.index]}" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  tags = { Name = "${var.project_name}-public-rt" }
}

resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${var.project_name}-private-rt" }
}

resource "aws_route_table_association" "private" {
  count          = 2
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}
```

- [ ] **Step 4: Security groups**

Create `infra/security_groups.tf`:

```hcl
# CloudFront's own IP range, not "the internet" — the ALB should only ever be reached
# through CloudFront, since CloudFront is what supplies the trusted TLS certificate.
data "aws_ec2_managed_prefix_list" "cloudfront" {
  name = "com.amazonaws.global.cloudfront.origin-facing"
}

resource "aws_security_group" "alb" {
  name        = "${var.project_name}-alb-sg"
  description = "Allow HTTP only from CloudFront's edge network"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    prefix_list_ids = [data.aws_ec2_managed_prefix_list.cloudfront.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "ecs" {
  name        = "${var.project_name}-ecs-sg"
  description = "Fargate tasks: inbound only from the ALB, outbound to pull images and reach RDS"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = var.container_port
    to_port         = var.container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "rds" {
  name        = "${var.project_name}-rds-sg"
  description = "PostgreSQL reachable only from ECS tasks"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

- [ ] **Step 5: ECR**

Create `infra/ecr.tf`:

```hcl
resource "aws_ecr_repository" "api" {
  name                 = "${var.project_name}-api"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name
  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep the last 10 tagged images"
        selection = {
          tagStatus   = "tagged"
          tagPrefixList = ["sha", "v"]
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = { type = "expire" }
      },
      {
        rulePriority = 2
        description  = "Expire untagged images after 1 day"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 1
        }
        action = { type = "expire" }
      }
    ]
  })
}
```

- [ ] **Step 6: S3**

Create `infra/s3.tf`:

```hcl
resource "aws_s3_bucket" "manuscripts" {
  bucket = "${var.project_name}-manuscripts-${data.aws_caller_identity.current.account_id}"
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
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "manuscripts" {
  bucket = aws_s3_bucket.manuscripts.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}
```

- [ ] **Step 7: Secrets Manager scaffolding**

Create `infra/secrets.tf`:

```hcl
resource "random_password" "db_password" {
  length  = 32
  special = false # avoid characters that need URL-encoding in a DSN
}

resource "random_id" "jwt_secret" {
  byte_length = 48
}

resource "aws_secretsmanager_secret" "database_url" {
  name = "ugjcs/database-url"
}

resource "aws_secretsmanager_secret" "jwt_secret" {
  name = "ugjcs/jwt-secret"
}

resource "aws_secretsmanager_secret_version" "jwt_secret" {
  secret_id     = aws_secretsmanager_secret.jwt_secret.id
  secret_string = random_id.jwt_secret.hex
}

# database_url's value is set in rds.tf (Task 3), because it needs the RDS endpoint,
# which does not exist yet.
```

- [ ] **Step 8: Outputs (extended in later tasks)**

Create `infra/outputs.tf`:

```hcl
output "ecr_repository_url" {
  value = aws_ecr_repository.api.repository_url
}

output "s3_bucket_name" {
  value = aws_s3_bucket.manuscripts.bucket
}

output "vpc_id" {
  value = aws_vpc.main.id
}

output "public_subnet_ids" {
  value = join(",", aws_subnet.public[*].id)
}

output "private_subnet_ids" {
  value = join(",", aws_subnet.private[*].id)
}

output "ecs_security_group_id" {
  value = aws_security_group.ecs.id
}

output "rds_security_group_id" {
  value = aws_security_group.rds.id
}
```

- [ ] **Step 9: Apply and verify**

```bash
cd infra
terraform init
terraform validate
terraform apply -target=aws_vpc.main -target=aws_subnet.public -target=aws_subnet.private \
  -target=aws_security_group.alb -target=aws_security_group.ecs -target=aws_security_group.rds \
  -target=aws_ecr_repository.api -target=aws_s3_bucket.manuscripts \
  -target=aws_secretsmanager_secret.jwt_secret -target=aws_secretsmanager_secret_version.jwt_secret
```

Then verify:

```bash
aws ec2 describe-subnets --filters "Name=tag:Name,Values=ugjcs-*" \
  --query 'Subnets[].{Id:SubnetId,AZ:AvailabilityZone,CIDR:CidrBlock}' --output table
```

Expected: 4 rows, 2 AZs, matching the CIDRs in `variables.tf`.

- [ ] **Step 10: Commit**

```bash
git add infra/providers.tf infra/variables.tf infra/networking.tf infra/security_groups.tf \
  infra/ecr.tf infra/s3.tf infra/secrets.tf infra/outputs.tf infra/.gitignore
git commit -m "feat: provision VPC, security groups, ECR, S3 and secrets scaffolding"
```

---

### Task 3: Terraform — RDS PostgreSQL and the ALB

**Files:**
- Create: `infra/rds.tf`, `infra/alb.tf`
- Modify: `infra/outputs.tf`

**Interfaces:**
- Produces: an RDS PostgreSQL 16 instance in the private subnets, the fully populated
  `ugjcs/database-url` secret, and an internet-facing ALB with a target group healthchecked
  on `/health`.

- [ ] **Step 1: RDS**

Create `infra/rds.tf`:

```hcl
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnets"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_db_instance" "main" {
  identifier             = "${var.project_name}-db"
  engine                 = "postgres"
  engine_version         = "16"
  instance_class         = var.db_instance_class
  allocated_storage      = 20
  storage_type           = "gp3"
  storage_encrypted      = true
  db_name                = var.db_name
  username               = var.db_username
  password               = random_password.db_password.result
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false
  multi_az               = false # cost decision: single-AZ is accepted for this assessment window
  backup_retention_period = 1
  skip_final_snapshot     = true
  deletion_protection     = false # must stay false so Task 9's teardown can run
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id = aws_secretsmanager_secret.database_url.id
  secret_string = "postgresql+asyncpg://${var.db_username}:${random_password.db_password.result}@${aws_db_instance.main.address}:5432/${var.db_name}"
}
```

- [ ] **Step 2: ALB**

Create `infra/alb.tf`:

```hcl
resource "aws_lb" "main" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id
}

resource "aws_lb_target_group" "api" {
  name        = "${var.project_name}-api-tg"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip" # required for awsvpc-networked Fargate tasks

  health_check {
    path                = var.health_check_path
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
    timeout             = 5
    matcher             = "200"
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}
```

- [ ] **Step 3: Outputs**

Append to `infra/outputs.tf`:

```hcl
output "rds_endpoint" {
  value     = aws_db_instance.main.address
  sensitive = true
}

output "alb_dns_name" {
  value = aws_lb.main.dns_name
}

output "alb_target_group_arn" {
  value = aws_lb_target_group.api.arn
}

output "database_url_secret_arn" {
  value = aws_secretsmanager_secret.database_url.arn
}

output "jwt_secret_arn" {
  value = aws_secretsmanager_secret.jwt_secret.arn
}
```

- [ ] **Step 4: Apply**

```bash
cd infra && terraform apply
```

RDS provisioning takes 5–10 minutes. Expected: `Apply complete!` with no errors.

- [ ] **Step 5: Verify RDS is reachable — from inside the VPC, not from a laptop**

RDS has no public route by design, so `psql` from a local machine cannot reach it; that is
correct, not a bug. Prove connectivity with a throwaway Fargate task instead:

```bash
CLUSTER_PLACEHOLDER=$(aws ecs list-clusters --query 'clusterArns[0]' --output text 2>/dev/null)
aws ecs run-task --cluster default --launch-type FARGATE --overrides '{}' \
  --task-definition arn:aws:ecs:eu-west-1::task-definition/dummy 2>&1 | head -1 || true
```

This exact connectivity proof belongs to Task 4, once the ECS cluster and task execution
role exist to run it with. For now, confirm the instance itself is healthy:

```bash
aws rds describe-db-instances --db-instance-identifier ugjcs-db \
  --query 'DBInstances[0].{Status:DBInstanceStatus,Endpoint:Endpoint.Address,SG:VpcSecurityGroups}'
```

Expected: `"Status": "available"`, an `Endpoint.Address` inside the VPC, and the security
group listed as `ugjcs-rds-sg`.

- [ ] **Step 6: Verify the ALB target group has no healthy targets yet — expected, not a failure**

```bash
aws elbv2 describe-target-health --target-group-arn "$(cd infra && terraform output -raw alb_target_group_arn)"
```

Expected: an empty `TargetHealthDescriptions` list. No ECS service exists until Task 4, so
there is nothing registered yet — this is the correct state to be in right now.

- [ ] **Step 7: Commit**

```bash
git add infra/rds.tf infra/alb.tf infra/outputs.tf
git commit -m "feat: provision RDS PostgreSQL and the application load balancer"
```

---

### Task 4: Terraform — ECS Fargate service and CloudFront

**Files:**
- Create: `infra/iam.tf`, `infra/ecs.tf`, `infra/cloudfront.tf`
- Modify: `infra/outputs.tf`

**Interfaces:**
- Produces: `ugjcs-ecs-execution-role`, `ugjcs-ecs-task-role`, ECS cluster `ugjcs-cluster`,
  service `ugjcs-api`, and a CloudFront distribution whose domain is the URL the examiner
  opens.

- [ ] **Step 1: IAM roles for ECS**

Create `infra/iam.tf`:

```hcl
data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecs_execution" {
  name               = "ugjcs-ecs-execution-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy_attachment" "ecs_execution_managed" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# The managed policy above does not include Secrets Manager access; without this, the
# container definition's `secrets` block (Step 3) cannot resolve UGJCS_DATABASE_URL or
# UGJCS_JWT_SECRET at task startup.
resource "aws_iam_role_policy" "ecs_execution_secrets" {
  name = "ugjcs-ecs-execution-secrets"
  role = aws_iam_role.ecs_execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "secretsmanager:GetSecretValue"
      Resource = [aws_secretsmanager_secret.database_url.arn, aws_secretsmanager_secret.jwt_secret.arn]
    }]
  })
}

resource "aws_iam_role" "ecs_task" {
  name               = "ugjcs-ecs-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy" "ecs_task_s3" {
  name = "ugjcs-ecs-task-s3"
  role = aws_iam_role.ecs_task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
      Resource = "${aws_s3_bucket.manuscripts.arn}/*"
    }]
  })
}
```

- [ ] **Step 2: Cluster and log group**

Create `infra/ecs.tf` (part 1):

```hcl
resource "aws_ecs_cluster" "main" {
  name = "ugjcs-cluster"
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/ugjcs-api"
  retention_in_days = 14
}
```

- [ ] **Step 3: Task definition and service**

Append to `infra/ecs.tf`:

```hcl
resource "aws_ecs_task_definition" "api" {
  family                   = "ugjcs-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "api"
      # Placeholder tag on first apply; Task 6's workflow registers the real image and
      # points the service at it. A task definition may reference a tag that does not
      # exist yet — the service will simply have no healthy tasks until Task 6 runs.
      image     = "${aws_ecr_repository.api.repository_url}:latest"
      essential = true
      portMappings = [{ containerPort = var.container_port, protocol = "tcp" }]
      environment = [{ name = "UGJCS_SQL_ECHO", value = "false" }]
      secrets = [
        { name = "UGJCS_DATABASE_URL", valueFrom = aws_secretsmanager_secret.database_url.arn },
        { name = "UGJCS_JWT_SECRET", valueFrom = aws_secretsmanager_secret.jwt_secret.arn }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.api.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "api"
        }
      }
    }
  ])

  # Terraform owns the shape of the task (cpu, memory, roles, secrets); the deploy
  # workflow owns which image tag is running. Without this, every `terraform apply` after
  # a deploy would revert the service back to the :latest placeholder.
  lifecycle {
    ignore_changes = [container_definitions]
  }
}

resource "aws_ecs_service" "api" {
  name            = "ugjcs-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name    = "api"
    container_port    = var.container_port
  }

  depends_on = [aws_lb_listener.http]

  lifecycle {
    ignore_changes = [task_definition]
  }
}
```

- [ ] **Step 4: CloudFront**

Create `infra/cloudfront.tf`:

```hcl
data "aws_cloudfront_cache_policy" "disabled" {
  name = "Managed-CachingDisabled"
}

data "aws_cloudfront_origin_request_policy" "all_viewer" {
  name = "Managed-AllViewer"
}

resource "aws_cloudfront_distribution" "api" {
  enabled     = true
  price_class = "PriceClass_100" # cheapest tier: US, Canada, Europe — sufficient for assessment

  origin {
    domain_name = aws_lb.main.dns_name
    origin_id   = "alb"
    custom_origin_config {
      http_port              = 80
      https_port              = 443
      origin_protocol_policy  = "http-only" # the ALB has no certificate; CloudFront supplies TLS to the reader
      origin_ssl_protocols    = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    allowed_methods          = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods            = ["GET", "HEAD"]
    target_origin_id          = "alb"
    viewer_protocol_policy    = "redirect-to-https"
    cache_policy_id           = data.aws_cloudfront_cache_policy.disabled.id
    origin_request_policy_id  = data.aws_cloudfront_origin_request_policy.all_viewer.id
  }

  restrictions {
    geo_restriction { restriction_type = "none" }
  }

  viewer_certificate {
    cloudfront_default_certificate = true # the *.cloudfront.net certificate — see plan header
  }
}
```

- [ ] **Step 5: Outputs**

Append to `infra/outputs.tf`:

```hcl
output "cloudfront_domain" {
  value = aws_cloudfront_distribution.api.domain_name
}

output "cloudfront_url" {
  value = "https://${aws_cloudfront_distribution.api.domain_name}"
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  value = aws_ecs_service.api.name
}
```

- [ ] **Step 6: Apply**

```bash
cd infra && terraform apply
```

CloudFront distributions take 5–15 minutes to reach `Deployed`. Expected: `Apply
complete!`. The ECS service will register but its tasks will fail to start (no valid image
yet at `:latest`) — this is expected here and resolved by Task 6.

- [ ] **Step 7: Verify the roles and cluster exist, and prove RDS connectivity from inside the VPC**

```bash
aws ecs describe-clusters --clusters ugjcs-cluster --query 'clusters[0].status'
```
Expected: `"ACTIVE"`.

Now prove the network path Fargate → RDS actually works, using a one-off task on the real
cluster and roles that now exist:

```bash
aws ecs run-task --cluster ugjcs-cluster --launch-type FARGATE \
  --task-definition ugjcs-api \
  --network-configuration "{\"awsvpcConfiguration\":{\"subnets\":[\"$(cd infra && terraform output -raw public_subnet_ids | cut -d, -f1)\"],\"securityGroups\":[\"$(cd infra && terraform output -raw ecs_security_group_id)\"],\"assignPublicIp\":\"ENABLED\"}}" \
  --overrides '{"containerOverrides":[{"name":"api","command":["python","-c","import socket,os; socket.create_connection((os.environ[\"PGHOST\"],5432),3); print(\"reachable\")"]}]}' \
  2>&1 | tail -5
```

This will fail with `CannotPullContainerError` until Task 6 pushes a real image — expected
at this point in the plan. Task 6's own verification step is where this connectivity proof
actually succeeds, once a working image exists. Record that this step is deferred, not
skipped.

- [ ] **Step 8: Commit**

```bash
git add infra/iam.tf infra/ecs.tf infra/cloudfront.tf infra/outputs.tf
git commit -m "feat: provision ECS Fargate service and CloudFront distribution"
```

---

### Task 5: Dockerfile for the FastAPI backend

**Files:**
- Create: `backend/Dockerfile`, `backend/.dockerignore`

**Interfaces:**
- Consumes: `ugjcs.api.main:app` (Plan 4 — confirm it exists before starting, per the
  cross-plan dependency note above).
- Produces: a multi-stage image running as a non-root user, listening on 8000.

- [ ] **Step 1: Confirm the precondition**

```bash
cd backend && uv run python -c "from ugjcs.api.main import app; print(app.routes and 'ok')"
```

Expected: `ok`. If this raises `ModuleNotFoundError`, stop — Plan 4 has not landed. Do not
improvise a stand-in app here (see the cross-plan dependency note at the top of this
document).

Confirm `fastapi` and `uvicorn[standard]` are in `backend/pyproject.toml`'s
`[project].dependencies`. If either is missing:

```bash
uv add fastapi "uvicorn[standard]"
```

- [ ] **Step 2: `.dockerignore`**

Create `backend/.dockerignore`:

```
.venv
.git
.mypy_cache
.ruff_cache
.pytest_cache
.hypothesis
.import_linter_cache
__pycache__
tests
*.pyc
.env
```

- [ ] **Step 3: Multi-stage Dockerfile**

Create `backend/Dockerfile`:

```dockerfile
# syntax=docker/dockerfile:1

FROM python:3.13-slim AS builder
RUN pip install --no-cache-dir "uv>=0.9,<0.10"
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
COPY alembic.ini ./
COPY alembic ./alembic
RUN uv sync --locked --no-dev

FROM python:3.13-slim AS runtime
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin ugjcs
WORKDIR /app
COPY --from=builder --chown=ugjcs:ugjcs /app /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
USER ugjcs
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request as u,sys; sys.exit(0 if u.urlopen('http://127.0.0.1:8000/health',timeout=3).status==200 else 1)"

CMD ["uvicorn", "ugjcs.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Two things worth stating explicitly: the build stage installs dependencies *before*
copying source (`--no-install-project` first) so an unchanged `uv.lock` reuses Docker's
layer cache on every source-only rebuild; and the runtime stage never installs `uv` at
all — only the already-built `.venv` is copied across, keeping the final image to
runtime dependencies only.

- [ ] **Step 4: Build and smoke-test locally**

```bash
cd backend
docker build -t ugjcs-api:local .
docker run --rm -d --name ugjcs-api-local -p 8000:8000 \
  -e UGJCS_DATABASE_URL=postgresql+asyncpg://postgres:pw@host.docker.internal:55432/ugjcs \
  -e UGJCS_JWT_SECRET=local-smoke-test-secret \
  ugjcs-api:local
sleep 3
curl -sf http://localhost:8000/health && echo OK
docker exec ugjcs-api-local whoami
docker rm -f ugjcs-api-local
```

Expected: `curl` returns HTTP 200 and prints `OK`; `whoami` prints `ugjcs`, not `root`.

- [ ] **Step 5: Commit**

```bash
git add backend/Dockerfile backend/.dockerignore
git commit -m "feat: add a multi-stage, non-root Dockerfile for the FastAPI backend"
```

---

### Task 6: Deploy workflow — build, push, migrate, deploy, smoke-test, roll back

**Files:**
- Create: `.github/workflows/deploy.yml`

**Interfaces:**
- Consumes: `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` (Task 1), `PUBLIC_SUBNET_IDS`,
  `ECS_SECURITY_GROUP_ID`, `CLOUDFRONT_URL` (Task 4's outputs, set as secrets below).
- Produces: the running `ugjcs-api` ECS service on the image built from `main`.

- [ ] **Step 1: Push the remaining secrets this workflow needs**

```bash
cd infra
gh secret set PUBLIC_SUBNET_IDS --repo rogerkorantenng/ugjcs --body "$(terraform output -raw public_subnet_ids)"
gh secret set ECS_SECURITY_GROUP_ID --repo rogerkorantenng/ugjcs --body "$(terraform output -raw ecs_security_group_id)"
gh secret set CLOUDFRONT_URL --repo rogerkorantenng/ugjcs --body "$(terraform output -raw cloudfront_url)"
gh secret list --repo rogerkorantenng/ugjcs
```

Expected: 5 secrets listed (2 from Task 1, 3 here).

- [ ] **Step 2: Write the workflow**

Create `.github/workflows/deploy.yml`:

```yaml
name: deploy

on:
  push:
    branches: [main]
    paths:
      - "backend/**"
      - ".github/workflows/deploy.yml"
  workflow_dispatch: {}

concurrency:
  group: deploy-production
  cancel-in-progress: false

permissions:
  contents: read

env:
  AWS_REGION: eu-west-1
  ECR_REPOSITORY: ugjcs-api
  ECS_CLUSTER: ugjcs-cluster
  ECS_SERVICE: ugjcs-api
  ECS_TASK_FAMILY: ugjcs-api
  CONTAINER_NAME: api

jobs:
  deploy:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Log in to ECR
        id: ecr-login
        uses: aws-actions/amazon-ecr-login@v2

      - name: Record the currently running task definition, for rollback
        run: |
          aws ecs describe-services --cluster "$ECS_CLUSTER" --services "$ECS_SERVICE" \
            --query 'services[0].taskDefinition' --output text > /tmp/previous_task_def.txt
          cat /tmp/previous_task_def.txt

      - name: Build and push the image
        id: build
        env:
          ECR_REGISTRY: ${{ steps.ecr-login.outputs.registry }}
        run: |
          IMAGE_URI="$ECR_REGISTRY/$ECR_REPOSITORY:${{ github.sha }}"
          docker build -t "$IMAGE_URI" .
          docker push "$IMAGE_URI"
          echo "image_uri=$IMAGE_URI" >> "$GITHUB_OUTPUT"

      - name: Register a new task definition revision with the new image
        id: render
        run: |
          aws ecs describe-task-definition --task-definition "$ECS_TASK_FAMILY" \
            --query 'taskDefinition' > /tmp/task-def.json
          python3 - <<'PY'
          import json
          with open("/tmp/task-def.json") as f:
              td = json.load(f)
          for key in ("taskDefinitionArn", "revision", "status", "requiresAttributes",
                      "compatibilities", "registeredAt", "registeredBy"):
              td.pop(key, None)
          for c in td["containerDefinitions"]:
              if c["name"] == "api":
                  c["image"] = "${{ steps.build.outputs.image_uri }}"
          with open("/tmp/new-task-def.json", "w") as f:
              json.dump(td, f)
          PY
          NEW_ARN=$(aws ecs register-task-definition --cli-input-json file:///tmp/new-task-def.json \
            --query 'taskDefinition.taskDefinitionArn' --output text)
          echo "task_def_arn=$NEW_ARN" >> "$GITHUB_OUTPUT"

      - name: Run Alembic migrations as a one-off ECS task
        run: |
          NETWORK_CONFIG=$(jq -n \
            --arg subnets "${{ secrets.PUBLIC_SUBNET_IDS }}" \
            --arg sg "${{ secrets.ECS_SECURITY_GROUP_ID }}" \
            '{awsvpcConfiguration:{subnets:($subnets|split(",")),securityGroups:[$sg],assignPublicIp:"ENABLED"}}')
          TASK_ARN=$(aws ecs run-task --cluster "$ECS_CLUSTER" \
            --task-definition "${{ steps.render.outputs.task_def_arn }}" \
            --launch-type FARGATE \
            --network-configuration "$NETWORK_CONFIG" \
            --overrides "{\"containerOverrides\":[{\"name\":\"$CONTAINER_NAME\",\"command\":[\"uv\",\"run\",\"alembic\",\"upgrade\",\"head\"]}]}" \
            --query 'tasks[0].taskArn' --output text)
          aws ecs wait tasks-stopped --cluster "$ECS_CLUSTER" --tasks "$TASK_ARN"
          EXIT_CODE=$(aws ecs describe-tasks --cluster "$ECS_CLUSTER" --tasks "$TASK_ARN" \
            --query 'tasks[0].containers[0].exitCode' --output text)
          echo "Migration task exit code: $EXIT_CODE"
          [ "$EXIT_CODE" = "0" ]

      - name: Update the service and wait for stability
        run: |
          aws ecs update-service --cluster "$ECS_CLUSTER" --service "$ECS_SERVICE" \
            --task-definition "${{ steps.render.outputs.task_def_arn }}" --force-new-deployment
          aws ecs wait services-stable --cluster "$ECS_CLUSTER" --services "$ECS_SERVICE"

      - name: Smoke-test the live health endpoint through CloudFront
        run: |
          for i in $(seq 1 10); do
            STATUS=$(curl -s -o /dev/null -w '%{http_code}' "${{ secrets.CLOUDFRONT_URL }}/health")
            if [ "$STATUS" = "200" ]; then echo "Healthy after attempt $i"; exit 0; fi
            sleep 6
          done
          echo "Health check never returned 200"; exit 1

      - name: Roll back on failure
        if: failure()
        run: |
          PREV=$(cat /tmp/previous_task_def.txt)
          echo "Rolling back to $PREV"
          aws ecs update-service --cluster "$ECS_CLUSTER" --service "$ECS_SERVICE" \
            --task-definition "$PREV" --force-new-deployment
          aws ecs wait services-stable --cluster "$ECS_CLUSTER" --services "$ECS_SERVICE"
```

- [ ] **Step 3: Trigger the first deployment**

```bash
git add .github/workflows/deploy.yml
git commit -m "ci: add the deploy workflow — build, push, migrate, deploy, smoke-test, roll back"
git push
gh workflow run deploy.yml --repo rogerkorantenng/ugjcs
gh run watch --repo rogerkorantenng/ugjcs
```

Expected: the run completes with conclusion `success`. If it fails at the migration step,
inspect the ECS task's CloudWatch logs (`/ecs/ugjcs-api`) before re-running — do not retry
blindly.

- [ ] **Step 4: Verify the service is genuinely healthy, not merely "not failed"**

```bash
aws ecs describe-services --cluster ugjcs-cluster --services ugjcs-api \
  --query 'services[0].{status:status,running:runningCount,desired:desiredCount}'
curl -s "$(cd infra && terraform output -raw cloudfront_url)/health"
```

Expected: `{"status": "ACTIVE", "running": 1, "desired": 1}`, and the health endpoint
returns HTTP 200 with a JSON body — reached through CloudFront, proving the whole chain
from edge to container.

---

### Task 7: Vercel — frontend deployment configuration

**Files:**
- Modify: Vercel project environment variables (no repository files required beyond what
  Plan 5 already created).

**Interfaces:**
- Consumes: `cloudfront_url` (Task 4's output).
- Produces: a live `*.vercel.app` deployment with `API_BASE_URL` set to the CloudFront
  origin.

Per the design spec §7.2, the browser never calls the backend directly — public archive
pages are server-rendered/ISR and authenticated traffic is proxied through Next.js route
handlers running server-side. `API_BASE_URL` is therefore a **server-only** variable
(no `NEXT_PUBLIC_` prefix); it must never be exposed to the client bundle.

- [ ] **Step 1: Human action — link the Vercel project**

**This step requires an interactive browser login and cannot be scripted.** From the
frontend directory:

```bash
cd frontend
vercel login
vercel link
```

Follow the prompts to link to (or create) the `ugjcs` Vercel project. Report back once
linked.

- [ ] **Step 2: Set the environment variable**

```bash
CLOUDFRONT_URL=$(cd ../infra && terraform output -raw cloudfront_url)
echo -n "$CLOUDFRONT_URL" | vercel env add API_BASE_URL production
echo -n "$CLOUDFRONT_URL" | vercel env add API_BASE_URL preview
vercel env ls
```

Expected: `API_BASE_URL` listed for both `production` and `preview`.

- [ ] **Step 3: Deploy**

```bash
vercel --prod
```

Expected: output ends with a `https://*.vercel.app` URL and `Production: <url>`.

- [ ] **Step 4: Verify the frontend is live**

```bash
FRONTEND_URL=$(vercel ls --prod 2>/dev/null | grep -o 'https://[^ ]*' | head -1)
curl -sI "$FRONTEND_URL" | head -1
```

Expected: `HTTP/2 200`. Deeper verification — that the frontend can actually reach the
backend through the BFF route handlers — happens in Task 9, from outside both networks.

---

### Task 8: Seed script — demonstration corpus and judge credentials

**Files:**
- Create: `backend/scripts/seed_demo.py`
- Modify (create): `Deployment_and_Source_Links.txt`

**Interfaces:**
- Consumes: `Account`, `EmailAddress`, `Role`, `Argon2PasswordHasher`,
  `SqlAlchemyUnitOfWork`, `Manuscript`, `TrackingCode` (see Interfaces inherited).
- Produces: 5 pre-verified accounts (one per role) and 3 demonstration manuscripts; a
  `Deployment_and_Source_Links.txt` with the live URL and every credential.

Plan 3 recorded explicitly that self-service email verification cannot reach an assessor's
inbox within the 48-hour window (SES sandbox), and that "test accounts must be seeded
pre-verified" as the accepted resolution. This task is that resolution.

- [ ] **Step 1: Write the seed script**

Create `backend/scripts/seed_demo.py`:

```python
"""Seed the demonstration corpus and the judge-facing accounts.

Idempotent: re-running skips any account or manuscript that already exists rather than
raising a duplicate-key error, so it is safe to run again after a redeploy.

Run as a one-off ECS task (see Step 2) so it executes inside the VPC and can reach RDS,
which has no public route.
"""

import asyncio
import os
from datetime import UTC, datetime
from uuid import uuid4

from ugjcs.domain.account import Account, EmailAddress
from ugjcs.domain.enums import Role
from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.infrastructure.db.engine import create_engine, session_factory
from ugjcs.infrastructure.db.uow import SqlAlchemyUnitOfWork
from ugjcs.infrastructure.security.passwords import Argon2PasswordHasher

DEMO_PASSWORD = os.environ.get("UGJCS_SEED_PASSWORD", "Ugjcs#Demo2026")
NOW = datetime.now(UTC)

DEMO_ACCOUNTS = [
    ("author@ugjcs.test", "Ama Owusu", Role.AUTHOR),
    ("reviewer@ugjcs.test", "Kwame Asante", Role.REVIEWER),
    ("editor@ugjcs.test", "Efua Mensah", Role.EDITOR),
    ("eic@ugjcs.test", "Kojo Boateng", Role.EDITOR_IN_CHIEF),
    ("admin@ugjcs.test", "Roger Koranteng Obeng", Role.ADMINISTRATOR),
]

DEMO_CORPUS = [
    "Sparse Retrieval for Low-Resource Ghanaian Languages",
    "Fair Scheduling for Shared University GPU Clusters",
    "Edge Caching Strategies for Campus Networks",
]


async def seed_accounts(uow: SqlAlchemyUnitOfWork) -> dict[str, UserId]:
    hasher = Argon2PasswordHasher()
    ids: dict[str, UserId] = {}
    async with uow:
        for email, name, role in DEMO_ACCOUNTS:
            existing = await uow.accounts.get_by_email(EmailAddress(email))
            if existing is not None:
                ids[email] = existing.id
                continue
            account = Account(
                id=UserId(uuid4()),
                email=EmailAddress(email),
                password_hash=hasher.hash(DEMO_PASSWORD),
                full_name=name,
                affiliation="University of Ghana",
            )
            account.grant(role)
            account.verify(occurred_at=NOW)
            await uow.accounts.add(account)
            ids[email] = account.id
        await uow.commit()
    return ids


async def seed_corpus(uow: SqlAlchemyUnitOfWork, account_ids: dict[str, UserId]) -> int:
    author_id = account_ids["author@ugjcs.test"]
    editor_id = account_ids["editor@ugjcs.test"]
    created = 0
    async with uow:
        for i, title in enumerate(DEMO_CORPUS, start=1):
            code = TrackingCode.mint(2026, i)
            if await uow.manuscripts.get_by_tracking_code(code) is not None:
                continue
            manuscript = Manuscript(
                id=ManuscriptId(uuid4()),
                tracking_code=code,
                title=title,
                abstract=f"A demonstration abstract for '{title}', seeded for assessment.",
                keywords=("demonstration",),
                author_ids=(author_id,),
                corresponding_author_id=author_id,
            )
            manuscript.submit(actor_id=author_id, occurred_at=NOW)
            if i == 2:  # advance one manuscript further, so the archive shows two states
                manuscript.begin_screening(actor_id=editor_id, occurred_at=NOW)
            await uow.manuscripts.add(manuscript)
            created += 1
        await uow.commit()
    return created


async def main() -> None:
    engine = create_engine()
    uow = SqlAlchemyUnitOfWork(session_factory(engine))
    account_ids = await seed_accounts(uow)
    manuscript_count = await seed_corpus(uow, account_ids)
    print(f"Seeded {len(account_ids)} accounts and {manuscript_count} new manuscripts.")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Run it as a one-off ECS task**

```bash
NETWORK_CONFIG=$(jq -n \
  --arg subnets "$(cd infra && terraform output -raw public_subnet_ids)" \
  --arg sg "$(cd infra && terraform output -raw ecs_security_group_id)" \
  '{awsvpcConfiguration:{subnets:($subnets|split(",")),securityGroups:[$sg],assignPublicIp:"ENABLED"}}')

TASK_ARN=$(aws ecs run-task --cluster ugjcs-cluster \
  --task-definition ugjcs-api \
  --launch-type FARGATE \
  --network-configuration "$NETWORK_CONFIG" \
  --overrides '{"containerOverrides":[{"name":"api","command":["uv","run","python","scripts/seed_demo.py"]}]}' \
  --query 'tasks[0].taskArn' --output text)

aws ecs wait tasks-stopped --cluster ugjcs-cluster --tasks "$TASK_ARN"
aws ecs describe-tasks --cluster ugjcs-cluster --tasks "$TASK_ARN" \
  --query 'tasks[0].containers[0].{exitCode:exitCode,reason:reason}'
```

Expected: `exitCode: 0`. If non-zero, read the task's log stream in `/ecs/ugjcs-api`
before retrying — the script is idempotent, so a retry after fixing the cause is safe.

- [ ] **Step 3: Write `Deployment_and_Source_Links.txt`**

Create `Deployment_and_Source_Links.txt` at the repository root:

```
UGJCS — University of Ghana Journal of Computing Science
Deployment and source links, prepared for assessment.

LIVE APPLICATION
  Frontend (open this):  https://<vercel-project>.vercel.app
  Backend API (CloudFront): https://<distribution-id>.cloudfront.net
  Backend health check:     https://<distribution-id>.cloudfront.net/health

SOURCE REPOSITORY
  https://github.com/rogerkorantenng/ugjcs

TEST CREDENTIALS  (password is shared across all five accounts below)
  Password: Ugjcs#Demo2026

  Author:            author@ugjcs.test
  Reviewer:           reviewer@ugjcs.test
  Editor:             editor@ugjcs.test
  Editor-in-Chief:    eic@ugjcs.test
  Administrator:      admin@ugjcs.test

NOTES FOR THE EXAMINER
  - All five accounts are pre-verified; no email confirmation step is required.
  - Three demonstration manuscripts are pre-seeded so the public archive is not empty.
  - Infrastructure is destroyed after assessment concludes (see the technical debt
    register and Plan 6's teardown task); this URL is not intended to remain live
    indefinitely.
```

Fill in the two placeholder URLs with the real values:

```bash
sed -i "s#<vercel-project>.vercel.app#$(vercel ls --prod 2>/dev/null | grep -o '[a-z0-9-]*\.vercel\.app' | head -1)#" Deployment_and_Source_Links.txt
CF_DOMAIN=$(cd infra && terraform output -raw cloudfront_domain)
sed -i "s#<distribution-id>.cloudfront.net#$CF_DOMAIN#g" Deployment_and_Source_Links.txt
cat Deployment_and_Source_Links.txt
```

- [ ] **Step 4: Commit**

```bash
git add backend/scripts/seed_demo.py Deployment_and_Source_Links.txt
git commit -m "feat: add demonstration seed script and judge credentials"
```

`Deployment_and_Source_Links.txt` contains a shared demo password by design — it is the
credentials file the submission explicitly requires, for accounts that hold no real data.
Do not reuse this password for anything else.

---

### Task 9: External verification, the optional worker module, and teardown

**Files:**
- Create: `infra/optional-worker/providers.tf`, `infra/optional-worker/variables.tf`,
  `infra/optional-worker/redis.tf`, `infra/optional-worker/worker.tf`,
  `infra/optional-worker/outputs.tf`

**Interfaces:**
- Produces: no change to the required deployment; documents an optional module and closes
  the plan with proof the whole path works from outside AWS entirely.

- [ ] **Step 1: Verify from outside — the public archive over HTTPS**

Run this from a machine that has never touched the VPC (a plain shell is enough; the point
is that nothing here uses an AWS CLI profile or VPC-internal networking):

```bash
curl -sf "$(cd infra && terraform output -raw cloudfront_url)/health" | jq .
```

Expected: HTTP 200, JSON body. This is the same check Task 6 ran from inside a GitHub
Actions runner; running it again from an ordinary machine confirms the path is reachable
from the public internet, not merely from AWS's own network.

- [ ] **Step 2: Verify login as a seeded test user**

```bash
FRONTEND_URL=$(cd frontend && vercel ls --prod 2>/dev/null | grep -o 'https://[^ ]*' | head -1)
curl -sf -X POST "$FRONTEND_URL/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"editor@ugjcs.test","password":"Ugjcs#Demo2026"}' -i | head -20
```

Expected: HTTP 200 with a `Set-Cookie` header — the BFF route handler exchanged the
credentials for a token and set the httpOnly session cookie, per the spec's §7.2
architecture. If Plan 4/5's login route uses a different path than `/api/auth/login`,
adjust to match; the point of this check is unchanged regardless of the exact path.

- [ ] **Step 3: Verify the API is reached through CloudFront, not only from inside the VPC**

```bash
dig +short "$(cd infra && terraform output -raw cloudfront_domain)" | head -3
curl -sv "$(cd infra && terraform output -raw cloudfront_url)/health" 2>&1 | grep -i "< HTTP\|x-cache"
```

Expected: `dig` resolves to CloudFront edge IPs (not the ALB's own IP); the response
carries an `X-Cache` header from CloudFront, confirming the request traversed the edge
network and not a direct ALB connection.

- [ ] **Step 4: The optional worker module — Redis and the `worker` ECS service**

Redis and a `worker` Fargate service are only needed once an asynchronous pipeline exists
(submission processing, reviewer matching). **No such pipeline exists in this codebase
yet**, so this module is written but deliberately **not applied**. It lives in its own
Terraform root with its own state, so applying it later is a separate, additive action
that never touches the required infrastructure above.

Create `infra/optional-worker/providers.tf`:

```hcl
terraform {
  required_version = ">= 1.10.5"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" {
  region  = "eu-west-1"
  profile = "ugjcs-deploy"
}
```

Create `infra/optional-worker/variables.tf`:

```hcl
variable "vpc_id" { description = "From the main module's `vpc_id` output" }
variable "private_subnet_ids" { description = "Comma-separated, from `private_subnet_ids`" }
variable "ecs_security_group_id" { description = "From `ecs_security_group_id`" }
variable "ecs_cluster_name" { default = "ugjcs-cluster" }
variable "ecs_execution_role_arn" { description = "From the main module's execution role" }
variable "ecs_task_role_arn" { description = "From the main module's task role" }
variable "database_url_secret_arn" {}
```

Create `infra/optional-worker/redis.tf`:

```hcl
resource "aws_security_group" "redis" {
  name   = "ugjcs-redis-sg"
  vpc_id = var.vpc_id
  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [var.ecs_security_group_id]
  }
  egress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_elasticache_subnet_group" "main" {
  name       = "ugjcs-redis-subnets"
  subnet_ids = split(",", var.private_subnet_ids)
}

resource "aws_elasticache_cluster" "main" {
  cluster_id           = "ugjcs-redis"
  engine               = "redis"
  node_type            = "cache.t4g.micro"
  num_cache_nodes      = 1
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [aws_security_group.redis.id]
}
```

Create `infra/optional-worker/worker.tf`:

```hcl
resource "aws_cloudwatch_log_group" "worker" {
  name              = "/ecs/ugjcs-worker"
  retention_in_days = 14
}

resource "aws_ecs_task_definition" "worker" {
  family                   = "ugjcs-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = var.ecs_execution_role_arn
  task_role_arn            = var.ecs_task_role_arn

  container_definitions = jsonencode([{
    name      = "worker"
    image     = "REPLACE-WITH-ecr_repository_url:latest" # same image, different entrypoint
    essential = true
    command   = ["uv", "run", "arq", "ugjcs.infrastructure.queue.WorkerSettings"]
    secrets = [{ name = "UGJCS_DATABASE_URL", valueFrom = var.database_url_secret_arn }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.worker.name
        "awslogs-region"        = "eu-west-1"
        "awslogs-stream-prefix" = "worker"
      }
    }
  }])
}

resource "aws_ecs_service" "worker" {
  name            = "ugjcs-worker"
  cluster         = var.ecs_cluster_name
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = 1
  launch_type     = "FARGATE"
  network_configuration {
    subnets          = split(",", var.private_subnet_ids)
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = false
  }
}
```

Create `infra/optional-worker/outputs.tf`:

```hcl
output "redis_endpoint" {
  value = aws_elasticache_cluster.main.cache_nodes[0].address
}
```

**Do not run `terraform apply` in this directory now.** It is committed so the queue can
be added later — when an async pipeline actually exists — with `cd
infra/optional-worker && terraform init && terraform apply` and the six variables above
supplied from the main module's outputs. Note the `worker` service is placed in the
**private** subnets (no public IP) since, unlike `api`, it needs no inbound ALB traffic —
add a NAT gateway or VPC endpoints at that point, since the worker will need to reach
ECR/Secrets Manager without a public IP of its own.

- [ ] **Step 5: Commit the optional module**

```bash
git add infra/optional-worker
git commit -m "feat: add an optional Redis/worker Terraform module, not applied"
```

- [ ] **Step 6: Document teardown — do not run it now**

**`terraform destroy` must not be run before the viva.** It is documented here so
teardown is a known, single command rather than something reconstructed under time
pressure afterwards:

```bash
# Run only after assessment concludes.
cd infra && terraform destroy
# If Task 9's optional module was ever applied, destroy it first:
# cd infra/optional-worker && terraform destroy
```

Expected, when eventually run: `Destroy complete! Resources: N destroyed.` with the RDS
instance skipping a final snapshot (`skip_final_snapshot = true`, set in Task 3) and the
ECR repository's images going with it — acceptable, since the source of truth is the Git
repository and the images are reproducible from it.

---

## Definition of done for Plan 6

- `aws sts get-caller-identity` shows the `ugjcs-deploy` IAM user, never root; root has MFA
  enabled; TD-01 in the technical debt register can be marked resolved.
- `aws ecs describe-services --cluster ugjcs-cluster --services ugjcs-api` reports `status:
  ACTIVE`, `runningCount == desiredCount == 1`.
- `curl https://<distribution>.cloudfront.net/health` returns HTTP 200 from a machine
  outside AWS entirely, and the response carries an `X-Cache` header proving it traversed
  CloudFront.
- The Vercel production deployment is live, `API_BASE_URL` points at the CloudFront origin,
  and logging in as `editor@ugjcs.test` through the frontend's BFF route succeeds.
- Five pre-verified accounts (author, reviewer, editor, editor-in-chief, administrator) and
  three demonstration manuscripts exist in the live database; their credentials are written
  into `Deployment_and_Source_Links.txt` at the repository root.
- The deploy workflow has run at least once end-to-end (build → push → migrate → deploy →
  smoke-test) with a `success` conclusion visible in `gh run list`.
- `infra/optional-worker/` exists, is documented as not-yet-applied, and requires no change
  to anything already running.
- `terraform destroy` is documented and has **not** been run.

## Human actions required — cannot be completed by an agent

1. **Enable MFA on the AWS root user** (Task 1, Step 6) — requires the AWS Console and a
   physical or virtual MFA device.
2. **`vercel login` / `vercel link`** (Task 7, Step 1) — requires an interactive browser
   OAuth flow.
3. **AWS service quota increases**, if the default account quota blocks any resource in
   Tasks 2–4 (new accounts occasionally start with a Fargate vCPU quota too low for even
   one task, or an RDS-per-region cap of zero for a given instance class). Watch for
   `RequestLimitExceeded` or `InsufficientCapacity` during `terraform apply`; if hit, file
   the increase from the AWS Console (Service Quotas) and wait — this can take minutes to
   hours and is outside this plan's control.
4. **GitHub repository visibility.** The repository is currently private. An examiner
   needs to open the source link in `Deployment_and_Source_Links.txt`; either add the
   examiner as a collaborator via `gh repo edit --add-collaborator` or make the repository
   public via `gh repo edit rogerkorantenng/ugjcs --visibility public`. This is a judgement
   call about what the assessment expects and is left to the person submitting the work.

## Deliberately not in this plan

Blue-green or canary deployment, autoscaling policies beyond the fixed `desired_count`,
WAF, multi-region failover, a remote Terraform state backend, and NAT gateways / VPC
endpoints for the `worker` service — all named explicitly in the scope discipline this plan
was given, and none of them changes whether an examiner can open a live URL and log in.

Redis and the `worker` ECS service are written in Task 9 but not applied, because no
asynchronous pipeline exists yet in this codebase to run on them — building the
infrastructure for a subsystem that does not exist would be exactly the kind of
gold-plating this plan was told to avoid.

## Carried forward

- TD-01 is resolved by Task 1; update `docs/04-technical-debt-register.md` to record that.
- TD-04 (the audit chain's external anchor) is untouched by this plan — CloudWatch Logs
  gives operational visibility into the running service, not a cryptographic anchor for
  `editorial_events`. That debt stands as recorded.
- The IAM policy in Task 1 is workable but not minimal; several `Describe*` and `logs:*`
  grants are broader than a fully least-privilege policy would allow, traded for the time
  available. Worth another pass once the account is not also under a 48-hour deadline.
