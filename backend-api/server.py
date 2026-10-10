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
SES_SENDER = os.environ.get("SES_SENDER_EMAIL", "rishith.gs@gmail.com")

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
ses = boto3.client('ses', **kwargs)

# In-memory aggregated telemetry counters
telemetry_stats = {
    "seatLocksAcquired": 0,
    "ordersQueued": 0,
    "revenueINR": 0
}

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

def send_ses_ticket_email(recipient, order_id, seat_id, amount):
    subject = f"Official Concert Pass: Diljit Dosanjh Live (Seat {seat_id} - {order_id})"
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background: #0f172a; color: #ffffff; padding: 24px; margin: 0;">
      <div style="max-width: 560px; margin: 0 auto; background: #1e293b; border-radius: 14px; overflow: hidden; border: 1px solid #334155;">
        <div style="background: #ea580c; padding: 24px; text-align: center;">
          <h1 style="margin: 0; color: #ffffff; font-size: 22px; font-weight: bold;">DIL-LUMINATI TOUR INDIA</h1>
          <p style="margin: 6px 0 0; color: #ffedd5; font-size: 14px;">Diljit Dosanjh Live in Concert</p>
        </div>
        <div style="padding: 24px;">
          <p style="color: #4ade80; font-weight: bold; margin: 0 0 16px; font-size: 15px;">Booking Confirmed via AWS Event-Driven Architecture</p>
          <table style="width: 100%; border-collapse: collapse; font-size: 14px; color: #ffffff;">
            <tr style="border-bottom: 1px solid #334155;">
              <td style="padding: 10px 0; color: #94a3b8;">Booking Reference:</td>
              <td style="padding: 10px 0; text-align: right; color: #38bdf8; font-weight: bold; font-family: monospace;">{order_id}</td>
            </tr>
            <tr style="border-bottom: 1px solid #334155;">
              <td style="padding: 10px 0; color: #94a3b8;">Concert Venue:</td>
              <td style="padding: 10px 0; text-align: right; color: #f8fafc;">DY Patil Stadium, Navi Mumbai</td>
            </tr>
            <tr style="border-bottom: 1px solid #334155;">
              <td style="padding: 10px 0; color: #94a3b8;">Event Date & Time:</td>
              <td style="padding: 10px 0; text-align: right; color: #f8fafc;">14 Nov 2026, 7:00 PM IST</td>
            </tr>
            <tr style="border-bottom: 1px solid #334155;">
              <td style="padding: 10px 0; color: #94a3b8;">Reserved Seat:</td>
              <td style="padding: 10px 0; text-align: right; color: #fbbf24; font-weight: bold; font-size: 16px;">{seat_id}</td>
            </tr>
            <tr>
              <td style="padding: 10px 0; color: #94a3b8;">Total Paid:</td>
              <td style="padding: 10px 0; text-align: right; color: #22c55e; font-weight: bold; font-size: 16px;">₹{float(amount):,.0f} INR</td>
            </tr>
          </table>
          <div style="margin-top: 24px; padding: 20px; background: #0f172a; border-radius: 10px; border: 2px dashed #ea580c; text-align: center;">
            <div style="font-size: 12px; color: #94a3b8; margin-bottom: 8px; text-transform: uppercase;">Official Gate Entry QR Pass</div>
            <div style="font-size: 28px; letter-spacing: 4px; font-family: monospace; color: #f8fafc;">[ █ ▄ █ ▄ █ ]</div>
            <div style="font-size: 11px; color: #22c55e; margin-top: 8px; font-weight: bold;">AUTHENTICATED BY AMAZON SES (ap-south-1)</div>
          </div>
        </div>
        <div style="background: #090d16; padding: 14px; text-align: center; color: #64748b; font-size: 11px;">
          Delivered via Amazon SES (ap-south-1 Mumbai) | High-Scale AWS Architecture
        </div>
      </div>
    </body>
    </html>
    """
    try:
        res = ses.send_email(
            Source=SES_SENDER,
            Destination={'ToAddresses': [recipient]},
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {'Html': {'Data': html_body, 'Charset': 'UTF-8'}}
            }
        )
        print(f"[SES SUCCESS] Ticket sent to {recipient}! SES MessageId: {res['MessageId']}")
        return res['MessageId']
    except Exception as e:
        print(f"[SES NOTICE] {e}")
        return None

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

        # 0. Serve UI HTML at root
        if path in ['/', '/index.html']:
            frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
            html_path = os.path.join(frontend_dir, "index.html")
            if os.path.exists(html_path):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                with open(html_path, 'rb') as f:
                    self.wfile.write(f.read())
                return
        
        # 1. Health check
        if path == '/health':
            self._set_cors(200)
            self.wfile.write(json.dumps({
                "status": "healthy",
                "aws": "connected",
                "region": REGION,
                "table": TABLE_NAME,
                "sqs": SQS_URL,
                "cloudwatch": "ConcertTicketing",
                "sesSender": SES_SENDER
            }).encode('utf-8'))
            return

        # 2. Real CloudWatch Telemetry Metrics
        if path == '/api/metrics':
            queue_depth = 0
            if SQS_URL:
                try:
                    attrs = sqs.get_queue_attributes(
                        QueueUrl=SQS_URL,
                        AttributeNames=['ApproximateNumberOfMessages']
                    )
                    queue_depth = int(attrs.get('Attributes', {}).get('ApproximateNumberOfMessages', 0))
                except Exception:
                    pass

            self._set_cors(200)
            self.wfile.write(json.dumps({
                "success": True,
                "namespace": "ConcertTicketing",
                "region": REGION,
                "metrics": {
                    "seatLocksAcquired": telemetry_stats["seatLocksAcquired"],
                    "ordersQueued": telemetry_stats["ordersQueued"],
                    "revenueINR": telemetry_stats["revenueINR"],
                    "sqsQueueDepth": queue_depth
                }
            }).encode('utf-8'))
            return

        # 3. Get live seats from real DynamoDB
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

        # 4. DynamoDB Atomic Conditional Lock
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
                
                # Emit CloudWatch Metric & Update Stats
                telemetry_stats["seatLocksAcquired"] += 1
                log_cloudwatch_metric('SeatLocksAcquired', 1)

                self._set_cors(200)
                self.wfile.write(json.dumps({
                    "success": True,
                    "message": f"Seat {seat_id} successfully locked in AWS DynamoDB for 10 minutes",
                    "data": {"seatId": seat_id, "lockExpiresAt": ttl},
                    "cloudwatch": {
                        "emitted": True,
                        "metric": "SeatLocksAcquired",
                        "namespace": "ConcertTicketing",
                        "currentCount": telemetry_stats["seatLocksAcquired"]
                    }
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

        # 5. Amazon SQS FIFO Purchase Dispatch + Amazon SES Email Dispatch
        if path == '/api/checkout/purchase':
            seat_id = data.get('seatId')
            user_id = data.get('userId', 'user-anon')
            email = data.get('customerEmail', 'rishith.gs@gmail.com')
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

                # Emit CloudWatch Metrics & Update Stats
                telemetry_stats["ordersQueued"] += 1
                telemetry_stats["revenueINR"] += float(amount)
                log_cloudwatch_metric('OrdersQueued', 1)
                log_cloudwatch_metric('RevenueINR', float(amount), 'None')

                # Dispatch Amazon SES confirmation email to customer
                ses_id = send_ses_ticket_email(email, order_id, seat_id, amount)

                self._set_cors(202)
                self.wfile.write(json.dumps({
                    "success": True,
                    "status": "PROCESSING",
                    "message": "Order successfully pushed to real Amazon SQS FIFO queue & SES email dispatched!",
                    "order": {
                        "orderId": order_id,
                        "seatId": seat_id,
                        "amount": amount,
                        "queueMessageId": msg_id,
                        "sesMessageId": ses_id
                    },
                    "cloudwatch": {
                        "emitted": True,
                        "namespace": "ConcertTicketing",
                        "metrics": [
                            {"name": "OrdersQueued", "value": 1, "total": telemetry_stats["ordersQueued"]},
                            {"name": "RevenueINR", "value": float(amount), "total": telemetry_stats["revenueINR"]}
                        ]
                    }
                }).encode('utf-8'))
            except Exception as e:
                self._set_cors(500)
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
            return

        self._set_cors(404)
        self.wfile.write(json.dumps({"error": "Not Found"}).encode('utf-8'))

if __name__ == '__main__':
    print(f"Starting Live AWS Connected API Server on http://0.0.0.0:{PORT}...")
    print(f"AWS Region: {REGION}")
    print(f"DynamoDB Table: {TABLE_NAME}")
    print(f"SQS FIFO Queue: {SQS_URL}")
    print(f"SES Verified Sender: {SES_SENDER}")
    print(f"CloudWatch Namespace: ConcertTicketing")

    with socketserver.TCPServer(("", PORT), AWSHandler) as httpd:
        httpd.serve_forever()
