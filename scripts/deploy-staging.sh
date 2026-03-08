#!/usr/bin/env bash
# scripts/deploy-staging.sh — Build and deploy Lambda zips to staging.
#
# Packages each Lambda with the full backend/ source tree and bundled
# dependencies, then runs aws lambda update-function-code.
#
# Prerequisites:
#   - AWS credentials with axiom-staging Lambda update permissions
#   - python3 / pip available on PATH
#
# Usage:
#   ./scripts/deploy-staging.sh
#
set -euo pipefail

REGION="us-east-1"
DIST="dist/lambda"
# python3 -m pip works whether invoked locally (macOS) or in CI (actions/setup-python)
PIP="python3 -m pip"

deploy_function() {
  local fn_name="$1"
  local handler_src="$2"
  local pkg_dir="${DIST}/${fn_name}"

  echo "==> ${fn_name}: packaging"
  rm -rf "${pkg_dir}"
  mkdir -p "${pkg_dir}"

  # 1. Full backend source tree — preserves backend.src.* absolute imports
  cp -r backend "${pkg_dir}/"

  # 2. Binary dependencies: download manylinux wheel for Lambda (Linux x86_64)
  $PIP install --quiet \
    --target "${pkg_dir}" \
    --platform manylinux2014_x86_64 \
    --python-version 312 \
    --implementation cp \
    --only-binary :all: \
    psycopg2-binary

  # 3. Pure-Python dependencies not available in the Lambda runtime
  $PIP install --quiet \
    --target "${pkg_dir}" \
    python-dotenv \
    httpx \
    "boto3-stubs[bedrock-runtime]"

  # 4. Handler entrypoint at zip root — matches handler.lambda_handler in Terraform
  cp "${handler_src}" "${pkg_dir}/handler.py"

  # 5. Create zip
  local zip_path="${DIST}/${fn_name}.zip"
  (cd "${pkg_dir}" && zip -r -q "../${fn_name}.zip" .)
  echo "    packaged: ${zip_path} ($(du -sh "${zip_path}" | cut -f1))"

  # 6. Upload to Lambda
  echo "==> ${fn_name}: deploying"
  aws lambda update-function-code \
    --function-name "${fn_name}" \
    --zip-file "fileb://${zip_path}" \
    --region "${REGION}" \
    --output text \
    --query 'CodeSize' \
    | xargs -I{} echo "    deployed: {} bytes"

  # 7. Wait for the update to finish before smoke tests run
  aws lambda wait function-updated \
    --function-name "${fn_name}" \
    --region "${REGION}"
  echo "==> ${fn_name}: live"
}

deploy_function "axiom-staging-axiom-chat"       "backend/src/chat/handler.py"
deploy_function "axiom-staging-axiom-engagement" "backend/src/engagement/handler.py"
