import os
import sys
import boto3

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

env = {}
env_path = os.path.join(os.path.dirname(__file__), "..", "backend-api", ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                env[k] = v

region = env.get("AWS_REGION", "ap-south-1")
access_key = env.get("AWS_ACCESS_KEY_ID")
secret_key = env.get("AWS_SECRET_ACCESS_KEY")

ses = boto3.client(
    'ses',
    region_name=region,
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key
)

email = "rishith.gs@gmail.com"
subject = "Official Concert Pass: Diljit Dosanjh - DIL-LUMINATI Tour India (Seat PIT-01)"

html_body = """
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
          <td style="padding: 10px 0; text-align: right; color: #38bdf8; font-weight: bold; font-family: monospace;">ORD-MUM-892401</td>
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
          <td style="padding: 10px 0; text-align: right; color: #fbbf24; font-weight: bold; font-size: 16px;">PIT-01 (Fan Pit VIP)</td>
        </tr>
        <tr>
          <td style="padding: 10px 0; color: #94a3b8;">Total Paid:</td>
          <td style="padding: 10px 0; text-align: right; color: #22c55e; font-weight: bold; font-size: 16px;">₹11,999 INR</td>
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

print(f"Sending official ticket pass via Amazon SES to {email}...")
res = ses.send_email(
    Source=email,
    Destination={'ToAddresses': [email]},
    Message={
        'Subject': {'Data': subject, 'Charset': 'UTF-8'},
        'Body': {'Html': {'Data': html_body, 'Charset': 'UTF-8'}}
    }
)
print(f"[SUCCESS] Amazon SES MessageId: {res['MessageId']}")
print(f"Delivered directly to {email}!")
