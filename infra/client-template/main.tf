provider "aws" {
  region = var.aws_region
  # Credentials: configure IAM role or access keys for client account.

  default_tags {
    tags = {
      Project     = var.project
      Environment = var.environment
      ManagedBy   = "terraform"
      Repo        = "Connors-EO/axiom"
    }
  }
}

module "networking" {
  source = "git::ssh://git@github-everops/Connors-EO/everops-infra.git//modules/networking?ref=infra-v0.3.0"

  project           = var.project
  environment       = var.environment
  aws_account_id    = var.aws_account_id
  nat_gateway_count = 1
}

module "iam" {
  source = "git::ssh://git@github-everops/Connors-EO/everops-infra.git//modules/iam?ref=infra-v0.3.0"

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

module "compute" {
  source = "git::ssh://git@github-everops/Connors-EO/everops-infra.git//modules/compute?ref=infra-v0.3.0"

  project                  = var.project
  environment              = var.environment
  aws_account_id           = var.aws_account_id
  aws_region               = var.aws_region
  vpc_id                   = module.networking.vpc_id
  private_subnet_ids       = module.networking.private_subnet_ids
  lambda_security_group_id = module.networking.lambda_security_group_id
  jwt_auth_enabled         = true
  oidc_issuer_url          = var.oidc_issuer_url
  jwt_audience             = var.jwt_audience

  function_configs = {
    "axiom-chat" = {
      role_arn        = module.iam.role_arns["axiom-chat"]
      memory_mb       = 1024
      timeout_seconds = 60
      environment_variables = {
        AXIOM_ENV     = var.environment
        DB_SECRET_ARN = var.db_secret_arn
      }
    }
    "axiom-engagement" = {
      role_arn        = module.iam.role_arns["axiom-engagement"]
      memory_mb       = 512
      timeout_seconds = 15
      environment_variables = {
        AXIOM_ENV     = var.environment
        DB_SECRET_ARN = var.db_secret_arn
      }
    }
  }
}
