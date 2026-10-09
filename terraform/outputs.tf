output "cloudfront_domain_name" {
  description = "CloudFront URL for accessing the frontend and API globally"
  value       = module.edge.cloudfront_domain_name
}

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = module.compute.alb_dns_name
}

output "rds_endpoint" {
  description = "Connection endpoint for PostgreSQL RDS"
  value       = module.database.rds_endpoint
}

output "dynamodb_table_name" {
  description = "DynamoDB table name for seat inventory & locks"
  value       = module.database.dynamodb_table_name
}

output "sqs_queue_url" {
  description = "SQS FIFO queue URL for purchases"
  value       = module.messaging.queue_url
}

output "frontend_s3_bucket" {
  description = "S3 bucket name where frontend static files are stored"
  value       = module.edge.s3_bucket_name
}
