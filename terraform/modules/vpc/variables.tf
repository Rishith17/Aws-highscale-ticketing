variable "project_name" {
  type        = string
  description = "Project identifier prefix"
}

variable "environment" {
  type        = string
  description = "Deployment environment (e.g. prod, staging, dev)"
}

variable "vpc_cidr" {
  type        = string
  default     = "10.0.0.0/16"
  description = "CIDR block for the VPC"
}

variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "AWS deployment region"
}
