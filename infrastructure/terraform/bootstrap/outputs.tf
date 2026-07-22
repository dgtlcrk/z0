output "terraform_state_bucket" {
  description = "S3 bucket containing Terraform state"
  value       = aws_s3_bucket.terraform_state.id
}

output "ecr_repository_url" {
  description = "Amazon ECR repository URL for z0"
  value       = aws_ecr_repository.z0.repository_url
}
