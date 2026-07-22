variable "aws_region" {
  description = "AWS region for z0 infrastructure"
  type        = string
  default     = "us-east-1"
}

variable "aws_account_id" {
  description = "AWS account ID used for globally unique resource names"
  type        = string
}
