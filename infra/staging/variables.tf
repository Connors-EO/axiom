variable "project" {
  type    = string
  default = "axiom"
}

variable "environment" {
  type    = string
  default = "staging"
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
  description = "IP CIDRs allowed through WAF (office, home, CI)"
  type        = list(string)
}

variable "db_secret_arn" {
  description = "ARN of the Secrets Manager secret for the database password"
  type        = string
}
