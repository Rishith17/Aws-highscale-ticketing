# 1. IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-lambda-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

# Lambda Policies: VPC execution, SQS consumption, DynamoDB update, SES send
resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy" "lambda_custom_policy" {
  name = "${var.project_name}-lambda-custom-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = var.sqs_queue_arn
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:UpdateItem",
          "dynamodb:GetItem"
        ]
        Resource = [var.dynamodb_table_arn, "${var.dynamodb_table_arn}/*"]
      },
      {
        Effect = "Allow"
        Action = [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ]
        Resource = "*"
      }
    ]
  })
}

# 2. Package Lambda code
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.root}/../lambda-order-processor"
  output_path = "${path.module}/lambda_order_processor.zip"
  excludes    = ["node_modules"]
}

# 3. AWS Lambda Function
resource "aws_lambda_function" "order_processor" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "${var.project_name}-order-processor"
  role             = aws_iam_role.lambda_role.arn
  handler          = "index.handler"
  runtime          = "nodejs20.x"
  timeout          = 30
  memory_size      = 256
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  vpc_config {
    subnet_ids         = var.private_compute_subnet_ids
    security_group_ids = [var.ec2_security_group_id]
  }

  environment {
    variables = {
      AWS_REGION          = var.aws_region
      DYNAMODB_TABLE_NAME = var.dynamodb_table_name
      DB_HOST             = var.rds_host
      DB_PORT             = "5432"
      DB_NAME             = var.db_name
      DB_USER             = var.db_user
      DB_PASSWORD         = var.db_password
      SES_SENDER_EMAIL    = var.ses_sender_email
    }
  }

  tags = {
    Name        = "${var.project_name}-order-processor"
    Environment = var.environment
  }
}

# 4. SQS FIFO Event Source Mapping
resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn = var.sqs_queue_arn
  function_name    = aws_lambda_function.order_processor.arn
  batch_size       = 10
  enabled          = true
}

# 5. Verified SES Email Identity for confirmations
resource "aws_ses_email_identity" "sender" {
  email = var.ses_sender_email
}
