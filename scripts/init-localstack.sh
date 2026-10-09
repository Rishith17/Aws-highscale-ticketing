#!/usr/bin/env bash
echo "Initializing LocalStack AWS resources for Ticketing System..."

# Create DynamoDB TicketInventory table
awslocal dynamodb create-table \
    --table-name TicketInventory \
    --attribute-definitions \
        AttributeName=PK,AttributeType=S \
        AttributeName=SK,AttributeType=S \
    --key-schema \
        AttributeName=PK,KeyType=HASH \
        AttributeName=SK,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1

# Enable TTL on lockExpiresAt
awslocal dynamodb update-time-to-live \
    --table-name TicketInventory \
    --time-to-live-specification "Enabled=true, AttributeName=lockExpiresAt" \
    --region us-east-1

# Create SQS FIFO Dead Letter Queue
awslocal sqs create-queue \
    --queue-name ticket-purchases-dlq.fifo \
    --attributes FifoQueue=true \
    --region us-east-1

# Create SQS FIFO Purchase Queue
DLQ_ARN=$(awslocal sqs get-queue-attributes --queue-url http://localhost:4566/000000000000/ticket-purchases-dlq.fifo --attribute-names QueueArn --query 'Attributes.QueueArn' --output text --region us-east-1)

awslocal sqs create-queue \
    --queue-name ticket-purchases.fifo \
    --attributes "FifoQueue=true,ContentBasedDeduplication=true,RedrivePolicy={\"deadLetterTargetArn\":\"${DLQ_ARN}\",\"maxReceiveCount\":\"3\"}" \
    --region us-east-1

# Verify SES Sender Identity
awslocal ses verify-email-identity --email-address tickets@cloud-ticketing.com --region us-east-1

echo "LocalStack AWS resources successfully provisioned!"
