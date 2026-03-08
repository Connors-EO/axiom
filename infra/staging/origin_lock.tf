# ---------------------------------------------------------------------------
# CloudFront → API Gateway origin locking
#
# CloudFront injects x-origin-verify: <secret> on every API request.
# The Lambda authorizer validates this header so that direct API Gateway
# calls (without CloudFront) return 403.
#
# Secret rotation is managed outside Terraform (lifecycle ignore_changes).
# ---------------------------------------------------------------------------

# ─── Random secret value ──────────────────────────────────────────────────────

resource "random_password" "origin_verify" {
  length  = 32
  special = false
}

# ─── Secrets Manager secret ───────────────────────────────────────────────────

resource "aws_secretsmanager_secret" "origin_verify" {
  name        = "axiom-staging-origin-verify"
  description = "CloudFront x-origin-verify header secret"
  kms_key_id  = "arn:aws:kms:us-east-1:${var.aws_account_id}:key/b3f9a8d5-0b3c-4063-a0c1-0fae7de8e167"

  tags = {
    Environment = "staging"
    ManagedBy   = "terraform"
    Project     = "axiom"
  }
}

resource "aws_secretsmanager_secret_version" "origin_verify" {
  secret_id     = aws_secretsmanager_secret.origin_verify.id
  secret_string = jsonencode({ value = random_password.origin_verify.result })

  lifecycle {
    ignore_changes = [secret_string]
  }
}

# ─── IAM role for origin-verify Lambda ───────────────────────────────────────

resource "aws_iam_role" "origin_authorizer" {
  name                 = "axiom-staging-origin-authorizer-role"
  permissions_boundary = module.iam.boundary_policy_arn

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "origin_authorizer_basic" {
  role       = aws_iam_role.origin_authorizer.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "origin_authorizer_secrets" {
  name = "axiom-staging-origin-authorizer-secrets"
  role = aws_iam_role.origin_authorizer.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "ReadOriginVerifySecret"
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = aws_secretsmanager_secret.origin_verify.arn
    }]
  })
}

# ─── Lambda package ───────────────────────────────────────────────────────────

data "archive_file" "origin_authorizer" {
  type        = "zip"
  source_file = "${path.root}/../../backend/src/authorizer/handler.py"
  output_path = "${path.root}/../../dist/origin_authorizer.zip"
}

# ─── Lambda function ─────────────────────────────────────────────────────────

resource "aws_lambda_function" "origin_authorizer" {
  function_name    = "axiom-staging-origin-authorizer"
  role             = aws_iam_role.origin_authorizer.arn
  runtime          = "python3.12"
  handler          = "handler.handler"
  filename         = data.archive_file.origin_authorizer.output_path
  source_code_hash = data.archive_file.origin_authorizer.output_base64sha256
  timeout          = 5
  memory_size      = 128

  environment {
    variables = {
      ORIGIN_VERIFY_SECRET_NAME = aws_secretsmanager_secret.origin_verify.name
    }
  }

  tags = {
    Environment = "staging"
    ManagedBy   = "terraform"
    Project     = "axiom"
  }
}
