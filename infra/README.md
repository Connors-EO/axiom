# Axiom Infrastructure

Terraform root modules for Axiom deployments. These consume modules from
[Connors-EO/everops-infra](https://github.com/Connors-EO/everops-infra).

## Structure

- `staging/` — EverOps staging environment (auto-applies on merge to main)
- `production/` — EverOps production environment (manual approval required)
- `client-template/` — Template for client sovereign deployments

## Deploying
```bash
cd infra/staging
terraform init
terraform plan
terraform apply
```

## Module versions

Module source tags are pinned in each main.tf. To upgrade a module version,
update the `?ref=infra-vX.Y.Z` tag and run `terraform init -upgrade`.

## State backend

State is stored in S3 bucket `axiom-tfstate-everops` with DynamoDB locking.
The staging and production environments use separate state keys.
