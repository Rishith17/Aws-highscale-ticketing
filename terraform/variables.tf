variable "project_name" {
  type        = string
  default     = "cloud-tickets"
  description = "Project name prefix for resources"
}

variable "environment" {
  type        = string
  default     = "prod"
  description = "Deployment environment"
}

variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "Primary AWS region"
}

variable "vpc_cidr" {
  type        = string
  default     = "10.0.0.0/16"
  description = "VPC CIDR block"
}

variable "db_password" {
  type        = string
  sensitive   = true
  description = "Master password for RDS database"
}

variable "custom_domain_name" {
  type        = string
  default     = ""
  description = "Optional custom Route 53 domain name"
}

variable "route53_zone_id" {
  type        = string
  default     = ""
  description = "Optional Route 53 hosted zone ID"
}
