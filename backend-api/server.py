import http.server
import socketserver
import json
import boto3
import time
from urllib.parse import urlparse

import os

PORT = int(os.environ.get("PORT", 8080))
REGION = os.environ.get("AWS_REGION", "ap-south-1")
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME", "TicketInventory")
SQS_URL = os.environ.get("SQS_QUEUE_URL", "")

# Load from .env if present
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                if k == "AWS_ACCESS_KEY_ID" and not AWS_ACCESS_KEY:
                    AWS_ACCESS_KEY = v
                elif k == "AWS_SECRET_ACCESS_KEY" and not AWS_SECRET_KEY:
                    AWS_SECRET_KEY = v
                elif k == "SQS_QUEUE_URL" and not SQS_URL:
                    SQS_URL = v

# Initialize Boto3 AWS Clients
kwargs = {"region_name": REGION}
if AWS_ACCESS_KEY and AWS_SECRET_KEY:
    kwargs["aws_access_key_id"] = AWS_ACCESS_KEY
    kwargs["aws_secret_access_key"] = AWS_SECRET_KEY

ddb = boto3.client('dynamodb', **kwargs)
sqs = boto3.client('sqs', **kwargs)
cw = boto3.client('cloudwatch', **kwargs)

def log_cloudwatch_metric(name, value, unit='Count'):
    try:
        cw.put_metric_data(
            Namespace='ConcertTicketing',
            MetricData=[{
                'MetricName': name,
                'Value': value,
                'Unit': unit,
                'Timestamp': time.time()
            }]
        )
    except Exception as e:
        print(f"[CW WARN] Metric {name} error: {e}")

class AWSHandler(http.server.BaseHTTPRequestHandler):
    def _set_cors(self, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_cors(200)

    def do_GET(self):
        path = urlparse(self.path).path
        
        # 1. Health check
        if path == '/health':
            self._set_cors(200)
            self.wfile.write(json.dumps({
                "status": "healthy",
                "aws": "connected",
                "region": REGION,
                "table": TABLE_NAME,
                "sqs": SQS_URL
            }).encode('utf-8'))
            return

        # 2. Get live seats from real DynamoDB
        if '/api/events/' in path and '/seats' in path:
            try:
                event_id = 'ev-diljit-mumbai'
                res = ddb.query(
                    TableName=TABLE_NAME,
                    KeyConditionExpression='PK = :pk AND begins_with(SK, :skPrefix)',
                    ExpressionAttributeValues={
                        ':pk': {'S': f'EVENT#{event_id}'},
                        ':skPrefix': {'S': 'SEAT#'}
                    }
                )
                now = int(time.time())
                seats = []
                for item in res.get('Items', []):
                    status = item.get('status', {}).get('S', 'AVAILABLE')
                    ttl = int(item.get('lockExpiresAt', {}).get('N', 0)) if 'lockExpiresAt' in item else 0
                    if status == 'LOCKED' and ttl and ttl <= now:
                        status = 'AVAILABLE'
                    
                    seats.append({
                        "seatId": item.get('seatId', {}).get('S', item['SK']['S'].replace('SEAT#', '')),
                        "tier": item.get('tier', {}).get('S', 'General'),
                        "price": float(item.get('price', {}).get('N', 1499)),
                        "status": status
                    })
                
                self._set_cors(200)
                self.wfile.write(json.dumps({"success": True, "data": seats}).encode('utf-8'))
            except Exception as e:
                self._set_cors(500)
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
            return

        self._set_cors(404)
        self.wfile.write(json.dumps({"error": "Not Found"}).encode('utf-8'))

    def do_POST(self):
        path = urlparse(self.path).path
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        data = json.loads(body.decode('utf-8')) if body else {}

        # 3. DynamoDB Atomic Conditional Lock
        if path == '/api/checkout/lock':
            seat_id = data.get('seatId')
            user_id = data.get('userId', 'user-anon')
            event_id = data.get('eventId', 'ev-diljit-mumbai')
            now = int(time.time())
            ttl = now + 600 # 10 mins

            try:
                ddb.update_item(
                    TableName=TABLE_NAME,
                    Key={
                        'PK': {'S': f'EVENT#{event_id}'},
                        'SK': {'S': f'SEAT#{seat_id}'}
                    },
                    UpdateExpression='SET #st = :locked, lockedByUserId = :uid, lockExpiresAt = :ttl',
                    ConditionExpression='attribute_not_exists(#st) OR #st = :avail OR lockExpiresAt < :now',
                    ExpressionAttributeNames={'#st': 'status'},
                    ExpressionAttributeValues={
                        ':locked': {'S': 'LOCKED'},
                        ':avail': {'S': 'AVAILABLE'},
                        ':uid': {'S': user_id},
                        ':ttl': {'N': str(ttl)},
                        ':now': {'N': str(now)}
                    }
                )
                # Emit CloudWatch Metric
                log_cloudwatch_metric('SeatLocksAcquired', 1)

                self._set_cors(200)
                self.wfile.write(json.dumps({
                    "success": True,
                    "message": f"Seat {seat_id} successfully locked in AWS DynamoDB for 10 minutes",
                    "data": {"seatId": seat_id, "lockExpiresAt": ttl}
                }).encode('utf-8'))
            except ddb.exceptions.ConditionalCheckFailedException:
                self._set_cors(409)
                self.wfile.write(json.dumps({
                    "success": False,
                    "message": f"Seat {seat_id} is already reserved by another customer!"
                }).encode('utf-8'))
            except Exception as e:
                self._set_cors(500)
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
            return

        # 4. Amazon SQS FIFO Purchase Dispatch
        if path == '/api/checkout/purchase':
            seat_id = data.get('seatId')
            user_id = data.get('userId', 'user-anon')
            email = data.get('customerEmail', 'customer@gmail.com')
            amount = data.get('amount', 1499)
            event_id = data.get('eventId', 'ev-diljit-mumbai')
            order_id = f"ORD-MUM-{int(time.time())}"

            try:
                # Push to Real SQS FIFO Queue
                res = sqs.send_message(
                    QueueUrl=SQS_URL,
                    MessageBody=json.dumps({
                        "orderId": order_id,
                        "seatId": seat_id,
                        "userId": user_id,
                        "customerEmail": email,
                        "amount": amount,
                        "eventId": event_id
                    }),
                    MessageGroupId=f"EVENT-{event_id}",
                    MessageDeduplicationId=f"{order_id}-{seat_id}"
                )
                msg_id = res['MessageId']

                # Mark DynamoDB seat as SOLD
                ddb.update_item(
                    TableName=TABLE_NAME,
                    Key={
                        'PK': {'S': f'EVENT#{event_id}'},
                        'SK': {'S': f'SEAT#{seat_id}'}
                    },
                    UpdateExpression='SET #st = :sold, finalizedOrderId = :oid REMOVE lockExpiresAt',
                    ExpressionAttributeNames={'#st': 'status'},
                    ExpressionAttributeValues={
                        ':sold': {'S': 'SOLD'},
                        ':oid': {'S': order_id}
                    }
                )

                # Emit CloudWatch Metrics
                log_cloudwatch_metric('OrdersQueued', 1)
                log_cloudwatch_metric('RevenueINR', float(amount), 'None')

                self._set_cors(202)
                self.wfile.write(json.dumps({
                    "success": True,
                    "status": "PROCESSING",
                    "message": "Order successfully pushed to real Amazon SQS FIFO queue!",
                    "order": {
                        "orderId": order_id,
                        "seatId": seat_id,
                        "amount": amount,
                        "queueMessageId": msg_id
                    }
                }).encode('utf-8'))
            except Exception as e:
                self._set_cors(500)
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
            return

        self._set_cors(404)
        self.wfile.write(json.dumps({"error": "Not Found"}).encode('utf-8'))

print(f"Starting Live AWS Connected API Server on http://0.0.0.0:{PORT}...")
print(f"AWS Region: {REGION}")
print(f"DynamoDB Table: {TABLE_NAME}")
print(f"SQS FIFO Queue: {SQS_URL}")

with socketserver.TCPServer(("", PORT), AWSHandler) as httpd:
    httpd.serve_forever()
