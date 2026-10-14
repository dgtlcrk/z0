terraform {
  required_version = ">= 1.10.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
  backend "s3" {}
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = "z0"
      Node        = "z0-cloud-01"
      Environment = "dev"
      ManagedBy   = "terraform"
    }
  }
}
