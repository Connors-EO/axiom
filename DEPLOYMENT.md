# Staging Deployment Runbook

## Prerequisites

- AWS SSO configured for the `everops-labs` profile (`aws configure sso`)
- Python 3.12 and `pip` on `PATH`
- Poetry installed (`pip install poetry`)
- `zip` and `aws` CLI available

## Authenticate

```bash
aws sso login --profile everops-labs
export AWS_PROFILE=everops-labs
```

## Deploy Lambda Code

The deploy script packages both Lambda handlers with their dependencies and
pushes them to the live staging functions.

```bash
./scripts/deploy-staging.sh
```

The script will:
1. Build a zip for each function containing the full `backend/` source tree
   and bundled dependencies (`psycopg2-binary`, `python-dotenv`, `httpx`,
   `boto3-stubs[bedrock-runtime]`)
2. Run `aws lambda update-function-code` for each function
3. Wait for each update to complete (`aws lambda wait function-updated`)

Functions deployed:
| Function name                     | Source                                   |
|-----------------------------------|------------------------------------------|
| `axiom-staging-axiom-chat`        | `backend/src/chat/handler.py`            |
| `axiom-staging-axiom-engagement`  | `backend/src/engagement/handler.py`      |

The `axiom-staging-origin-authorizer` is deployed automatically by Terraform
(`terraform apply`) and does not require a manual code push.

## Run Smoke Tests

```bash
export AWS_PROFILE=everops-labs
export AXIOM_STAGING_URL=https://dzpaw9gvq8f8t.cloudfront.net

poetry install --with dev
poetry run pytest backend/tests/smoke/ -m smoke -v
```

### What runs vs. what skips

| Test | Condition |
|------|-----------|
| `test_origin_lock_rejects_direct_request` | Always runs |
| `test_create_engagement` | Skips — Cognito not yet deployed |
| `test_get_engagement` | Skips — Cognito not yet deployed |
| `test_list_engagements` | Skips — Cognito not yet deployed |
| `test_chat_turn` | Skips — Cognito not yet deployed |

Skipped tests are **not** failures. CI passes when origin-lock passes and all
other tests skip gracefully.

## Infrastructure

Terraform for the staging environment lives in `infra/staging/`. It is applied
automatically by `deploy-staging.yml` on every push to `main`.

To apply manually:

```bash
cd infra/staging
terraform init
terraform apply
```

## Environment Variables

| Variable | Where set | Description |
|----------|-----------|-------------|
| `AWS_PROFILE` | Local shell | SSO profile for the axiom account |
| `AXIOM_STAGING_URL` | GitHub secret + local shell | CloudFront URL for smoke tests |
| `TF_VAR_DB_SECRET_ARN` | GitHub secret | ARN of the RDS password secret |

## Rollback

To roll back a bad Lambda deploy, update the function code with the previous
zip or trigger a new CI run from the last good commit:

```bash
git revert HEAD
git push origin main
```

## Known Issues

### API Gateway route prefix mismatch

CloudFront forwards `/api/*` requests to the API Gateway with the full path
(including `/api/`), but the current API Gateway routes are `/health`,
`/chat`, `/engagements` (no `/api/` prefix). Until this is fixed:

- Requests through CloudFront at `/api/health` will return 404
- Smoke tests that go through CloudFront (Cognito-dependent tests) will not
  pass even when Cognito is deployed

**Fix**: Update `infra/staging/main.tf` to pass the `routes` variable with
`/api/` prefix:

```hcl
module "compute" {
  # ... existing config ...
  routes = {
    "POST /api/engagements/{id}/chat" = "axiom-chat"
    "GET /api/health"                 = "axiom-chat"
    "GET /api/engagements"            = "axiom-engagement"
    "POST /api/engagements"           = "axiom-engagement"
  }
}
```

### No RDS database

The RDS instance is not yet deployed. Both Lambda handlers will fail on
database connection. Resolves when Story 4.x (database) is completed.

### No Cognito

Cognito user pool and M2M client are not yet deployed (Story 4.11). Smoke
tests that require a JWT token will skip until Cognito is set up.
