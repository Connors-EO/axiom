output "cloudfront_domain_name" {
  value       = module.compute.cloudfront_domain_name
  description = "CloudFront domain"
}

output "api_endpoint" {
  value       = module.compute.api_endpoint
  description = "HTTP API Gateway endpoint"
}

output "function_names" {
  value       = module.compute.function_names
  description = "Lambda function names"
}

output "vpc_id" {
  value       = module.networking.vpc_id
  description = "VPC ID"
}
