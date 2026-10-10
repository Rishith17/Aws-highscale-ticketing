import os
import sys
import json
import time
import boto3

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

REGION = os.environ.get("AWS_REGION", "ap-south-1")
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
SQS_URL = os.environ.get("SQS_QUEUE_URL", "")
SENDER_EMAIL = os.environ.get("SES_SENDER_EMAIL", "rishith.gs@gmail.com")

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
    order_id = order.get("orderId", "ORD-001")
    seat = order.get("seatId", "SEAT-01")
    customer_email = order.get("customerEmail", "rishith.gs@gmail.com")
    amount = float(order.get("amount", 1499))

    # In SES Sandbox, route to the verified email
    recipient = "rishith.gs@gmail.com"

    subject = f"Official Concert Pass: Diljit Dosanjh Live (Seat {seat} - {order_id})"
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
              <td style="padding: 10px 0; color: #94a3b8;">Customer Account:</td>
              <td style="padding: 10px 0; text-align: right; color: #f8fafc;">{customer_email}</td>
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
              <td style="padding: 10px 0; text-align: right; color: #fbbf24; font-weight: bold; font-size: 16px;">{seat}</td>
            </tr>
            <tr>
              <td style="padding: 10px 0; color: #94a3b8;">Total Paid:</td>
              <td style="padding: 10px 0; text-align: right; color: #22c55e; font-weight: bold; font-size: 16px;">₹{amount:,.0f} INR</td>
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
        return False

def process_queue():
    print(f"Starting Layer 9 SQS Worker & SES Dispatcher...")
    print(f"Queue URL: {SQS_URL}")
    print(f"Verified Sender: {SENDER_EMAIL}")
    print(f"Polling for purchase messages in SQS FIFO...")

    while True:
        try:
            res = sqs.receive_message(
                QueueUrl=SQS_URL,
                MaxNumberOfMessages=5,
                WaitTimeSeconds=3
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
                
                # Deliver SES email
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
