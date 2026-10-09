#!/bin/bash
set -e

# Update packages and install Node.js 20 & Git
dnf update -y
dnf module enable nodejs:20 -y
dnf install -y nodejs git

# Setup App directory
mkdir -p /opt/ticket-api
cd /opt/ticket-api

# Create Environment File
cat <<EOF > /opt/ticket-api/.env
PORT=8080
AWS_REGION=${AWS_REGION}
DYNAMODB_TABLE_NAME=${DYNAMODB_TABLE_NAME}
SQS_QUEUE_URL=${SQS_QUEUE_URL}
DB_HOST=${DB_HOST}
DB_PORT=5432
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
NODE_ENV=production
EOF

# Create simple systemd service
cat <<EOF > /etc/systemd/system/ticket-api.service
[Unit]
Description=High-Scale Ticket API Server
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/ticket-api
EnvironmentFile=/opt/ticket-api/.env
ExecStart=/usr/bin/node /opt/ticket-api/src/server.js
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Clone or synchronize app code and start service
# systemctl daemon-reload
# systemctl enable --now ticket-api
