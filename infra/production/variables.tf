variable "project" {
  type    = string
  default = "axiom"
}

variable "environment" {
  type    = string
  default = "production"
}

variable "aws_account_id" {
  type    = string
  default = "289921858159"
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "allowed_ip_cidrs" {
  description = "IP CIDRs allowed through WAF (office, home, CI) — not used when jwt_auth_enabled = true"
  type        = list(string)
  default     = []
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
