import os
import sys
import boto3

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Load credentials from backend-api/.env
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

if not access_key or not secret_key:
    print("[ERROR] AWS credentials not found in backend-api/.env")
    sys.exit(1)

# Get email from argument or prompt
if len(sys.argv) > 1:
    email = sys.argv[1].strip()
else:
    email = input("Enter your email address to verify in Amazon SES: ").strip()

if not email or "@" not in email or email == "your-email@gmail.com":
    print("[ERROR] Please provide a valid real email address.")
    print("Usage: python scripts/verify_ses_email.py yourname@gmail.com")
    sys.exit(1)

print(f"Connecting to Amazon SES in {region}...")
ses = boto3.client(
    'ses',
    region_name=region,
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key
)

try:
    ses.verify_email_identity(EmailAddress=email)
    print(f"\n[SUCCESS] Verification email sent to: {email}")
    print("[INFO] AWS has sent an email titled: 'Amazon SES Address Verification Request'")
    print("[ACTION REQUIRED] Open your inbox, click the verification link inside.")
    print("[NEXT STEP] Once verified, run: python scripts/process_orders_worker.py to deliver e-tickets!")
except Exception as e:
    print(f"[ERROR] Failed to request verification: {e}")
