terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  type        = string
  default     = "ap-south-1" # Asia Pacific (Mumbai)
  description = "AWS Region to deploy all resources"
}

variable "db_password" {
  type        = string
  default     = "ConcertDbSecure123!"
  sensitive   = true
  description = "Master password for PostgreSQL database"
}

variable "ses_email" {
  type        = string
  default     = "your-email@gmail.com"
  description = "Your email address to receive concert ticket confirmations"
}

# ==============================================================================
# 1. NETWORKING (Simple Default VPC or Dedicated VPC)
# ==============================================================================
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Security Group for EC2 & RDS
resource "aws_security_group" "concert_sg" {
  name        = "concert-ticketing-sg"
  description = "Allow HTTP, app port 8080, and internal DB access"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "HTTP Public"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "App Port 8080"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "PostgreSQL Internal"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    self        = true
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ==============================================================================
# 2. DYNAMODB (Step 7 in Diagram: Seat Availability & 10-Min Atomic Hold)
# ==============================================================================
resource "aws_dynamodb_table" "ticket_inventory" {
  name         = "TicketInventory"
  billing_mode = "PAY_PER_REQUEST" # On-Demand (Free tier friendly)
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  ttl {
    attribute_name = "lockExpiresAt"
    enabled        = true
  }

  tags = {
    Name = "TicketInventory"
  }
}

# ==============================================================================
# 3. SQS FIFO QUEUE (Step 8 in Diagram: Purchase Queue to Prevent Crash)
# ==============================================================================
resource "aws_sqs_queue" "purchase_dlq" {
  name       = "ticket-purchases-dlq.fifo"
  fifo_queue = true
}

resource "aws_sqs_queue" "purchase_queue" {
  name                        = "ticket-purchases.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
  visibility_timeout_seconds  = 60

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.purchase_dlq.arn
    maxReceiveCount     = 3
  })
}

# ==============================================================================
# 4. RDS POSTGRESQL (Step 6 in Diagram: Permanent Orders Database)
# ==============================================================================
resource "aws_db_instance" "postgres" {
  identifier             = "concert-ticket-db"
  engine                 = "postgres"
  engine_version         = "15.4"
  instance_class         = "db.t4g.micro" # Economical / Free Tier eligible
  allocated_storage      = 20
  db_name                = "ticketdb"
  username               = "dbadmin"
  password               = var.db_password
  vpc_security_group_ids = [aws_security_group.concert_sg.id]
  skip_final_snapshot    = true
  publicly_accessible    = false

  tags = {
    Name = "ConcertTicketDB"
  }
}

# ==============================================================================
# 5. AMAZON SES & LAMBDA WORKER (Step 9 in Diagram: Order Finalizer & Emailer)
# ==============================================================================
resource "aws_ses_email_identity" "sender" {
  email = var.ses_email
}

resource "aws_iam_role" "lambda_role" {
  name = "concert-lambda-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy" "lambda_app_perms" {
  name = "concert-lambda-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
        Resource = aws_sqs_queue.purchase_queue.arn
      },
      {
        Effect   = "Allow"
        Action   = ["dynamodb:UpdateItem", "dynamodb:GetItem"]
        Resource = [aws_dynamodb_table.ticket_inventory.arn, "${aws_dynamodb_table.ticket_inventory.arn}/*"]
      },
      {
        Effect   = "Allow"
        Action   = ["ses:SendEmail", "ses:SendRawEmail"]
        Resource = "*"
      }
    ]
  })
}

# Lambda Source Zip
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.root}/../lambda-order-processor"
  output_path = "${path.module}/lambda.zip"
  excludes    = ["node_modules"]
}

resource "aws_lambda_function" "order_processor" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "concert-order-processor"
  role             = aws_iam_role.lambda_role.arn
  handler          = "index.handler"
  runtime          = "nodejs20.x"
  timeout          = 30
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  vpc_config {
    subnet_ids         = data.aws_subnets.default.ids
    security_group_ids = [aws_security_group.concert_sg.id]
  }

  environment {
    variables = {
      AWS_REGION          = var.aws_region
      DYNAMODB_TABLE_NAME = aws_dynamodb_table.ticket_inventory.name
      DB_HOST             = aws_db_instance.postgres.address
      DB_PORT             = "5432"
      DB_NAME             = "ticketdb"
      DB_USER             = "dbadmin"
      DB_PASSWORD         = var.db_password
      SES_SENDER_EMAIL    = var.ses_email
    }
  }
}

# SQS Trigger for Lambda
resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn = aws_sqs_queue.purchase_queue.arn
  function_name    = aws_lambda_function.order_processor.arn
  batch_size       = 10
}

# ==============================================================================
# 6. EC2 INSTANCE (Step 5 in Diagram: Running the Backend Node API)
# ==============================================================================
data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }
}

resource "aws_iam_role" "ec2_role" {
  name = "concert-ec2-api-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "ec2_perms" {
  name = "concert-ec2-policy"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["dynamodb:*"]
        Resource = [aws_dynamodb_table.ticket_inventory.arn, "${aws_dynamodb_table.ticket_inventory.arn}/*"]
      },
      {
        Effect   = "Allow"
        Action   = ["sqs:SendMessage", "sqs:GetQueueAttributes"]
        Resource = aws_sqs_queue.purchase_queue.arn
      }
    ]
  })
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "concert-ec2-instance-profile"
  role = aws_iam_role.ec2_role.name
}

resource "aws_instance" "backend_api" {
  ami                  = data.aws_ami.amazon_linux_2023.id
  instance_type        = "t3.micro"
  iam_instance_profile = aws_iam_instance_profile.ec2_profile.name
  vpc_security_group_ids = [aws_security_group.concert_sg.id]

  user_data = <<-EOF
              #!/bin/bash
              dnf update -y
              dnf module enable nodejs:20 -y
              dnf install -y nodejs git
              
              mkdir -p /opt/concert-api
              cd /opt/concert-api
              
              # Write environment file with live AWS resource values
              cat <<ENVEOF > /opt/concert-api/.env
              PORT=8080
              AWS_REGION=${var.aws_region}
              DYNAMODB_TABLE_NAME=${aws_dynamodb_table.ticket_inventory.name}
              SQS_QUEUE_URL=${aws_sqs_queue.purchase_queue.url}
              DB_HOST=${aws_db_instance.postgres.address}
              DB_PORT=5432
              DB_NAME=ticketdb
              DB_USER=dbadmin
              DB_PASSWORD=${var.db_password}
              ENVEOF
              
              EOF

  tags = {
    Name = "ConcertTicketingAPI"
  }
}

# ==============================================================================
# OUTPUTS
# ==============================================================================
output "ec2_public_ip" {
  description = "Public IP of your EC2 Backend Server"
  value       = aws_instance.backend_api.public_ip
}

output "dynamodb_table" {
  value = aws_dynamodb_table.ticket_inventory.name
}

output "sqs_queue_url" {
  value = aws_sqs_queue.purchase_queue.url
}

output "rds_endpoint" {
  value = aws_db_instance.postgres.address
}

output "lambda_function_name" {
  value = aws_lambda_function.order_processor.function_name
}
