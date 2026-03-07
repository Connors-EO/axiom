provider "aws" {
  region = var.aws_region
  # Credentials: set AWS_PROFILE=everops-labs locally (SSO),
  # or export AWS_ACCESS_KEY_ID/SECRET/SESSION_TOKEN (CI via OIDC).

  default_tags {
    tags = {
      Project     = "axiom"
      Environment = var.environment
      ManagedBy   = "terraform"
      Repo        = "Connors-EO/axiom"
    }
  }
}

module "networking" {
  source = "git::https://github.com/Connors-EO/everops-infra.git//modules/networking?ref=infra-v0.3.0"

  project           = var.project
  environment       = var.environment
  aws_account_id    = var.aws_account_id
  nat_gateway_count = 1
}

module "iam" {
  source = "git::https://github.com/Connors-EO/everops-infra.git//modules/iam?ref=infra-v0.3.0"

  project        = var.project
  environment    = var.environment
  aws_account_id = var.aws_account_id
  functions = {
    "axiom-chat" = {
      allowed_actions = [
        "bedrock:InvokeModel",
        "rds-db:connect",
        "secretsmanager:GetSecretValue"
      ]
      resource_arns = [
        "arn:aws:bedrock:${var.aws_region}:${var.aws_account_id}:*",
        "arn:aws:rds-db:${var.aws_region}:${var.aws_account_id}:dbuser/*/*",
        "arn:aws:secretsmanager:${var.aws_region}:${var.aws_account_id}:secret:axiom-*"
      ]
    }
    "axiom-engagement" = {
      allowed_actions = [
        "rds-db:connect",
        "secretsmanager:GetSecretValue"
      ]
      resource_arns = [
        "arn:aws:rds-db:${var.aws_region}:${var.aws_account_id}:dbuser/*/*",
        "arn:aws:secretsmanager:${var.aws_region}:${var.aws_account_id}:secret:axiom-*"
      ]
    }
  }
}

# ---------------------------------------------------------------------------
# GitHub Actions OIDC — deploy role for CI pipeline
# The OIDC provider for token.actions.githubusercontent.com already exists
# in this account; reference it via data source.
# ---------------------------------------------------------------------------

data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

resource "aws_iam_role" "github_actions" {
  name = "axiom-github-actions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = data.aws_iam_openid_connect_provider.github.arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringLike = {
          "token.actions.githubusercontent.com:sub" = "repo:Connors-EO/axiom:*"
        }
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })

  tags = {
    Project     = "axiom"
    Environment = "staging"
    ManagedBy   = "terraform"
  }
}

resource "aws_iam_role_policy" "github_actions" {
  name = "axiom-github-actions-policy"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "LambdaDeploy"
        Effect = "Allow"
        Action = [
          "lambda:UpdateFunctionCode",
          "lambda:GetFunction",
          "lambda:ListFunctions"
        ]
        Resource = "arn:aws:lambda:us-east-1:${var.aws_account_id}:function:axiom-staging-*"
      },
      {
        Sid    = "TerraformState"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::axiom-tfstate-everops",
          "arn:aws:s3:::axiom-tfstate-everops/*"
        ]
      },
      {
        Sid    = "TerraformLock"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:DeleteItem"
        ]
        Resource = "arn:aws:dynamodb:us-east-1:${var.aws_account_id}:table/axiom-tfstate-lock"
      },
      {
        Sid    = "TerraformKMS"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = "arn:aws:kms:us-east-1:${var.aws_account_id}:key/*"
        Condition = {
          StringEquals = {
            "kms:RequestAlias" = "alias/axiom-tfstate"
          }
        }
      }
    ]
  })
}

module "compute" {
  source = "git::https://github.com/Connors-EO/everops-infra.git//modules/compute?ref=infra-v0.3.0"

  project                  = var.project
  environment              = var.environment
  aws_account_id           = var.aws_account_id
  aws_region               = var.aws_region
  vpc_id                   = module.networking.vpc_id
  private_subnet_ids       = module.networking.private_subnet_ids
  lambda_security_group_id = module.networking.lambda_security_group_id
  jwt_auth_enabled         = false
  allowed_ip_cidrs         = var.allowed_ip_cidrs

  function_configs = {
    "axiom-chat" = {
      role_arn        = module.iam.role_arns["axiom-chat"]
      memory_mb       = 1024
      timeout_seconds = 60
      environment_variables = {
        AXIOM_ENV     = "staging"
        DB_SECRET_ARN = var.db_secret_arn
      }
    }
    "axiom-engagement" = {
      role_arn        = module.iam.role_arns["axiom-engagement"]
      memory_mb       = 512
      timeout_seconds = 15
      environment_variables = {
        AXIOM_ENV     = "staging"
        DB_SECRET_ARN = var.db_secret_arn
      }
    }
  }
}
