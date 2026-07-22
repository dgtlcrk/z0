provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "z0"
      Environment = "shared"
      ManagedBy   = "Terraform"
    }
  }
}
