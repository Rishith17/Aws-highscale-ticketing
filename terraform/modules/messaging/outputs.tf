output "queue_url" {
  value = aws_sqs_queue.purchase_queue.url
}

output "queue_arn" {
  value = aws_sqs_queue.purchase_queue.arn
}

output "dlq_arn" {
  value = aws_sqs_queue.purchase_dlq.arn
}
