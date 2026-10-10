import os
import json
import time
import boto3

REGION = os.environ.get("AWS_REGION", "ap-south-1")
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
SQS_URL = os.environ.get("SQS_QUEUE_URL", "")
SENDER_EMAIL = os.environ.get("SES_SENDER_EMAIL", "tickets@concerts-india.com")

env_path = os.path.join(os.path.dirname(__file__), "..", "backend-api", ".env")
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

kwargs = {"region_name": REGION}
if AWS_ACCESS_KEY and AWS_SECRET_KEY:
    kwargs["aws_access_key_id"] = AWS_ACCESS_KEY
    kwargs["aws_secret_access_key"] = AWS_SECRET_KEY

sqs = boto3.client('sqs', **kwargs)
ses = boto3.client('ses', **kwargs)

def send_ticket_email(order):
    recipient = order.get("customerEmail", "customer@gmail.com")
    seat = order.get("seatId", "SEAT-01")
    order_id = order.get("orderId", "ORD-001")
    amount = order.get("amount", 1499)

    subject = f"🎟️ Booking Confirmed: Diljit Dosanjh Live (Seat {seat})"
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background: #0f172a; color: #ffffff; padding: 20px;">
        <div style="max-width: 500px; margin: 0 auto; background: #1e293b; border-radius: 12px; padding: 24px; border: 1px solid #334155;">
          <h2 style="color: #38bdf8; margin-top: 0;">🎟️ Diljit Dosanjh — DIL-LUMINATI Tour India</h2>
          <p><strong>Booking ID:</strong> {order_id}</p>
          <p><strong>Reserved Seat:</strong> {seat}</p>
          <p><strong>Amount Paid:</strong> ₹{amount:,.0f} INR</p>
          <p><strong>Venue:</strong> DY Patil Stadium, Navi Mumbai</p>
          <hr style="border: 0; border-top: 1px solid #334155; margin: 20px 0;" />
          <div style="text-align: center; padding: 16px; background: #0f172a; border-radius: 8px;">
            <p style="font-size: 12px; color: #94a3b8; margin: 0;">Scan at Stadium Gate Entry (QR CODE PASS)</p>
            <div style="font-size: 28px; margin: 10px 0;">[ █ ▄ █ ▄ █ ]</div>
            <p style="font-size: 11px; color: #22c55e; margin: 0;">VALIDATED • OFFICIAL ENTRY PASS</p>
          </div>
        </div>
      </body>
    </html>
    """

    try:
        response = ses.send_email(
            Source=SENDER_EMAIL,
            Destination={'ToAddresses': [recipient]},
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {'Html': {'Data': html_body, 'Charset': 'UTF-8'}}
            }
        )
        print(f" [SES SUCCESS] Sent email to {recipient}! SES MessageId: {response['MessageId']}")
        return True
    except Exception as e:
        print(f" [SES NOTICE] Could not deliver to {recipient}: {e}")
        print(f"   (Cause: AWS SES Sandbox requires verifying {recipient} or request production access)")
        return False

def process_queue():
    print(f"Starting Layer 9 SQS Worker & SES Dispatcher...")
    print(f"Queue URL: {SQS_URL}")
    print(f"Polling for purchase messages in SQS FIFO...")

    while True:
        try:
            res = sqs.receive_message(
                QueueUrl=SQS_URL,
                MaxNumberOfMessages=5,
                WaitTimeSeconds=5
            )
            messages = res.get('Messages', [])
            if not messages:
                print("No pending messages in queue. Waiting...")
                time.sleep(5)
                continue

            for msg in messages:
                receipt = msg['ReceiptHandle']
                body = json.loads(msg['Body'])
                print(f"\n[RECEIVED ORDER] OrderId: {body.get('orderId')} | Seat: {body.get('seatId')} | Email: {body.get('customerEmail')}")
                
                # Attempt SES delivery
                send_ticket_email(body)
                
                # Delete from SQS once processed
                sqs.delete_message(QueueUrl=SQS_URL, ReceiptHandle=receipt)
                print(f"[SQS COMMITTED] Message deleted from SQS FIFO queue.")
        except KeyboardInterrupt:
            print("Worker stopped.")
            break
        except Exception as e:
            print(f"Worker loop error: {e}")
            time.sleep(5)

if __name__ == '__main__':
    process_queue()
