variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "aws_account_id" {
  type    = string
  default = "209586344300"
}

variable "image_tag" {
  description = "Immutable Git commit-based ECR image tag; never use latest."
  type        = string
  default     = "f595462a6e7a"
  validation {
    condition     = can(regex("^[0-9a-f]{12}$", var.image_tag))
    error_message = "Use a 12-character Git commit SHA image tag."
  }
}

variable "vpc_cidr" {
  type    = string
  default = "10.80.0.0/16"
}

variable "irc_server" {
  description = "IRC server reachable from AWS; specify explicitly."
  type        = string
}

variable "irc_channel" {
  description = "Cloud bot channel; specify explicitly after verifying network authorization."
  type        = string
}

variable "irc_port" {
  description = "IRC port. Current application does not establish TLS automatically."
  type        = number
  default     = 6667
  validation {
    condition     = var.irc_port > 0 && var.irc_port <= 65535
    error_message = "Port must be between 1 and 65535."
  }
}

variable "irc_nick" {
  type    = string
  default = "z0_cloud_01"
}

variable "irc_op_secret_arn" {
  description = "Existing Secrets Manager secret ARN for IRC_OP_SECRET, or null to disable OP authentication."
  type        = string
  default     = null
  nullable    = true
}
