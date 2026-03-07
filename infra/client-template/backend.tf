terraform {
  backend "s3" {
    # Replace with client-specific values
    bucket         = "REPLACE_WITH_CLIENT_TFSTATE_BUCKET"
    key            = "axiom/REPLACE_WITH_CLIENT_NAME/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    kms_key_id     = "alias/REPLACE_WITH_CLIENT_KMS_ALIAS"
    dynamodb_table = "REPLACE_WITH_CLIENT_TFSTATE_LOCK_TABLE"
  }
}
