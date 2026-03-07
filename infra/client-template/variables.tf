variable "project" {
  type    = string
  default = "axiom"
}

variable "environment" {
  description = "Client environment name (e.g. client-acme)"
  type        = string
}

variable "aws_account_id" {
  description = "Client AWS account ID"
  type        = string
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "db_secret_arn" {
  description = "ARN of the Secrets Manager secret for the database password"
  type        = string
}

variable "oidc_issuer_url" {
  description = "OIDC issuer URL for JWT authorizer"
  type        = string
}

variable "jwt_audience" {
  description = "JWT audience for API Gateway JWT authorizer"
  type        = list(string)
}
