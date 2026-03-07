terraform {
  backend "s3" {
    bucket         = "axiom-tfstate-everops"
    key            = "axiom/production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    kms_key_id     = "alias/axiom-tfstate"
    dynamodb_table = "axiom-tfstate-lock"
  }
}
