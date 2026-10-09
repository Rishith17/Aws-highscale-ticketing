variable "project_name" { type = string }
variable "environment" { type = string }
variable "alb_dns_name" { type = string }
variable "custom_domain_name" {
  type        = string
  default     = ""
  description = "Optional custom Route 53 domain name"
}
variable "route53_zone_id" {
  type        = string
  default     = ""
  description = "Optional Route 53 public hosted zone ID"
}
