variable "project_name" { type = string }
variable "environment" { type = string }
variable "vpc_id" { type = string }
variable "public_subnet_ids" { type = list(string) }
variable "private_compute_subnet_ids" { type = list(string) }
variable "alb_security_group_id" { type = string }
variable "ec2_security_group_id" { type = string }

variable "dynamodb_table_arn" { type = string }
variable "dynamodb_table_name" { type = string }
variable "sqs_queue_arn" { type = string }
variable "sqs_queue_url" { type = string }

variable "rds_host" { type = string }
variable "db_name" { type = string }
variable "db_user" { type = string }
variable "db_password" { type = string; sensitive = true }

variable "instance_type" {
  type    = string
  default = "t3.medium"
}
