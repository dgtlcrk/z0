variable "enable_bot" {
  description = "Safety gate: start the 24/7 ECS service only after IRC TLS and readiness review."
  type        = bool
  default     = false
}

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
  default     = "a129e165da94"
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
  description = "IRC server for standalone cloud node."
  type        = string
  default     = "irc.prison.net"
  validation {
    condition     = var.irc_server == "irc.prison.net"
    error_message = "This deployment is restricted to irc.prison.net."
  }
}

variable "irc_channel" {
  description = "IRC channel for cloud BotOps."
  type        = string
  default     = "#skipland"
}

variable "irc_port" {
  description = "IRC TLS port for the cloud node."
  type        = number
  default     = 6697
  validation {
    condition     = var.irc_port > 0 && var.irc_port <= 65535
    error_message = "Port must be between 1 and 65535."
  }
}

variable "irc_nick" {
  type    = string
  default = "z0_cloud_01"
}

variable "irc_tls_ca_secret_arn" {
  description = "Existing Secrets Manager ARN for independently verified irc.prison.net PEM certificate."
  type        = string
  default     = null
  nullable    = true
}

variable "irc_op_secret_arn" {
  description = "Existing Secrets Manager secret ARN for IRC_OP_SECRET, or null to disable OP authentication."
  type        = string
  default     = null
  nullable    = true
}
