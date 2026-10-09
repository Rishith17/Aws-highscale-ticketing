variable "project_name" { type = string }
variable "environment" { type = string }
variable "private_db_subnet_ids" { type = list(string) }
variable "rds_security_group_id" { type = string }

variable "db_name" {
  type    = string
  default = "ticketdb"
}

variable "db_username" {
  type    = string
  default = "dbadmin"
}

variable "db_password" {
  type        = string
  sensitive   = true
  description = "Master password for RDS database"
}
