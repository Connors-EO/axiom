# ---------------------------------------------------------------------------
# GitHub Actions OIDC CI Roles
#
# Two roles implement least-privilege CI:
#   plan  — read-only, trusted by all repo events (PR checks)
#   apply — full CRUD, trusted by main-branch pushes only
#
# IAM write actions on the apply role are conditioned on PermissionsBoundary
# to prevent privilege escalation; the boundary policy itself and the
# apply role's own trust are protected by explicit Deny statements.
# ---------------------------------------------------------------------------

locals {
  oidc_provider_arn   = data.aws_iam_openid_connect_provider.github.arn
  boundary_policy_arn = "arn:aws:iam::${var.aws_account_id}:policy/AxiomLambdaBoundary-staging"
  apply_role_arn      = "arn:aws:iam::${var.aws_account_id}:role/axiom-github-actions-apply-role"
}

data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

# ── Plan role (read-only, all repo events) ────────────────────────────────

resource "aws_iam_role" "github_actions_plan" {
  name = "axiom-github-actions-plan-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = local.oidc_provider_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringLike   = { "token.actions.githubusercontent.com:sub" = "repo:Connors-EO/axiom:*" }
        StringEquals = { "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com" }
      }
    }]
  })
}

resource "aws_iam_role_policy" "github_actions_plan" {
  name = "axiom-github-actions-plan-policy"
  role = aws_iam_role.github_actions_plan.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "TerraformStateRead"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:ListBucket"]
        Resource = [
          "arn:aws:s3:::axiom-tfstate-everops",
          "arn:aws:s3:::axiom-tfstate-everops/*"
        ]
      },
      {
        Sid      = "TerraformLockRead"
        Effect   = "Allow"
        Action   = ["dynamodb:GetItem"]
        Resource = "arn:aws:dynamodb:us-east-1:${var.aws_account_id}:table/axiom-tfstate-lock"
      },
      {
        Sid    = "TerraformKMSDecrypt"
        Effect = "Allow"
        Action = ["kms:Decrypt"]
        Resource = "arn:aws:kms:us-east-1:${var.aws_account_id}:key/*"
        Condition = {
          "ForAnyValue:StringEquals" = { "kms:ResourceAliases" = "alias/axiom-tfstate" }
        }
      },
      {
        Sid      = "EC2Read"
        Effect   = "Allow"
        Action   = ["ec2:Describe*"]
        Resource = "*"
      },
      {
        Sid      = "IAMRead"
        Effect   = "Allow"
        Action   = ["iam:Get*", "iam:List*"]
        Resource = "*"
      },
      {
        Sid    = "LambdaRead"
        Effect = "Allow"
        Action = [
          "lambda:GetFunction", "lambda:ListFunctions", "lambda:GetFunctionConfiguration",
          "lambda:GetPolicy", "lambda:ListTags", "lambda:ListVersionsByFunction",
          "lambda:GetFunctionCodeSigningConfig"
        ]
        Resource = "*"
      },
      {
        Sid      = "APIGatewayRead"
        Effect   = "Allow"
        Action   = ["apigateway:GET"]
        Resource = "*"
      },
      {
        Sid    = "CloudFrontRead"
        Effect = "Allow"
        Action = ["cloudfront:Get*", "cloudfront:List*"]
        Resource = "*"
      },
      {
        Sid    = "WAFRead"
        Effect = "Allow"
        Action = ["wafv2:Get*", "wafv2:List*"]
        Resource = "*"
      },
      {
        Sid    = "SecretsManagerRead"
        Effect = "Allow"
        Action = ["secretsmanager:DescribeSecret", "secretsmanager:GetSecretValue", "secretsmanager:ListSecrets", "secretsmanager:GetResourcePolicy"]
        Resource = "arn:aws:secretsmanager:us-east-1:${var.aws_account_id}:secret:axiom-*"
      },
      {
        Sid    = "S3BucketRead"
        Effect = "Allow"
        Action = [
          "s3:GetBucketVersioning", "s3:GetEncryptionConfiguration", "s3:GetBucketPublicAccessBlock",
          "s3:GetBucketPolicy", "s3:GetBucketTagging", "s3:GetBucketLocation",
          "s3:GetBucketCORS", "s3:GetBucketWebsite", "s3:GetBucketLogging",
          "s3:GetBucketObjectLockConfiguration", "s3:GetBucketAcl"
        ]
        Resource = "arn:aws:s3:::axiom-*"
      },
      {
        Sid    = "CloudWatchLogsRead"
        Effect = "Allow"
        Action = ["logs:DescribeLogGroups", "logs:ListTagsForResource", "logs:ListTagsLogGroup"]
        Resource = "*"
      },
      {
        Sid      = "STSIdentity"
        Effect   = "Allow"
        Action   = ["sts:GetCallerIdentity"]
        Resource = "*"
      }
    ]
  })
}

# ── Apply role (full CRUD, main-branch push only) ─────────────────────────

resource "aws_iam_role" "github_actions_apply" {
  name = "axiom-github-actions-apply-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = local.oidc_provider_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringLike   = { "token.actions.githubusercontent.com:sub" = "repo:Connors-EO/axiom:ref:refs/heads/main" }
        StringEquals = { "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com" }
      }
    }]
  })

  tags = {
    Project     = "axiom"
    Environment = "staging"
    ManagedBy   = "terraform"
  }
}

resource "aws_iam_role_policy" "github_actions_apply" {
  name = "axiom-github-actions-apply-policy"
  role = aws_iam_role.github_actions_apply.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "LambdaDeploy"
        Effect = "Allow"
        Action = [
          "lambda:UpdateFunctionCode",
          "lambda:GetFunction",
          "lambda:ListFunctions",
          "lambda:GetFunctionConfiguration",
          "lambda:UpdateFunctionConfiguration",
          "lambda:CreateFunction",
          "lambda:DeleteFunction",
          "lambda:AddPermission",
          "lambda:RemovePermission",
          "lambda:GetPolicy",
          "lambda:TagResource",
          "lambda:UntagResource",
          "lambda:ListTags"
        ]
        Resource = "arn:aws:lambda:us-east-1:${var.aws_account_id}:function:axiom-staging-*"
      },
      {
        Sid    = "TerraformState"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
        Resource = [
          "arn:aws:s3:::axiom-tfstate-everops",
          "arn:aws:s3:::axiom-tfstate-everops/*"
        ]
      },
      {
        Sid    = "TerraformLock"
        Effect = "Allow"
        Action = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DeleteItem"]
        Resource = "arn:aws:dynamodb:us-east-1:${var.aws_account_id}:table/axiom-tfstate-lock"
      },
      {
        Sid    = "TerraformKMS"
        Effect = "Allow"
        Action = ["kms:Decrypt", "kms:GenerateDataKey"]
        Resource = "arn:aws:kms:us-east-1:${var.aws_account_id}:key/*"
        Condition = {
          "ForAnyValue:StringEquals" = { "kms:ResourceAliases" = "alias/axiom-tfstate" }
        }
      },
      {
        Sid      = "EC2Manage"
        Effect   = "Allow"
        Action   = ["ec2:*"]
        Resource = "*"
      },
      {
        Sid    = "IAMRead"
        Effect = "Allow"
        Action = ["iam:Get*", "iam:List*"]
        Resource = "*"
      },
      {
        Sid    = "IAMWriteWithBoundary"
        Effect = "Allow"
        Action = [
          "iam:CreateRole",
          "iam:DeleteRole",
          "iam:UpdateRole",
          "iam:AttachRolePolicy",
          "iam:DetachRolePolicy",
          "iam:PutRolePolicy",
          "iam:DeleteRolePolicy",
          "iam:TagRole",
          "iam:UntagRole",
          "iam:PassRole",
          "iam:UpdateAssumeRolePolicy",
          "iam:CreateOpenIDConnectProvider",
          "iam:DeleteOpenIDConnectProvider",
          "iam:UpdateOpenIDConnectProviderThumbprint",
          "iam:AddClientIDToOpenIDConnectProvider",
          "iam:RemoveClientIDFromOpenIDConnectProvider",
          "iam:CreatePolicy",
          "iam:CreatePolicyVersion",
          "iam:SetDefaultPolicyVersion"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "iam:PermissionsBoundary" = local.boundary_policy_arn
          }
        }
      },
      {
        Sid    = "DenyBoundaryPolicyModification"
        Effect = "Deny"
        Action = [
          "iam:DeletePolicy",
          "iam:CreatePolicyVersion",
          "iam:SetDefaultPolicyVersion"
        ]
        Resource = local.boundary_policy_arn
      },
      {
        Sid      = "DenyRemoveBoundaryFromAnyRole"
        Effect   = "Deny"
        Action   = ["iam:DeleteRolePermissionsBoundary"]
        Resource = "*"
      },
      {
        Sid      = "DenyOwnTrustModification"
        Effect   = "Deny"
        Action   = ["iam:UpdateAssumeRolePolicy"]
        Resource = local.apply_role_arn
      }
    ]
  })
}
