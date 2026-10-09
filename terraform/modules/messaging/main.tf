# Dead Letter Queue (DLQ) for failed ticket purchase orders
resource "aws_sqs_queue" "purchase_dlq" {
  name                        = "${var.project_name}-purchases-dlq.fifo"
  fifo_queue                  = true
  message_retention_seconds   = 1209600 # 14 days
  sqs_managed_sse_enabled     = true
}

# Primary FIFO Queue for purchases
resource "aws_sqs_queue" "purchase_queue" {
  name                        = "${var.project_name}-purchases.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
  visibility_timeout_seconds  = 120
  message_retention_seconds   = 86400
  sqs_managed_sse_enabled     = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.purchase_dlq.arn
    maxReceiveCount     = 3
  })
}
