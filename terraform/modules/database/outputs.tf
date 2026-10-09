output "dynamodb_table_name" {
  value = aws_dynamodb_table.ticket_inventory.name
}

output "dynamodb_table_arn" {
  value = aws_dynamodb_table.ticket_inventory.arn
}

output "rds_endpoint" {
  value = aws_db_instance.postgres.endpoint
}

output "rds_address" {
  value = aws_db_instance.postgres.address
}
