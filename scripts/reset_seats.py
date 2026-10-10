import os
import sys
import boto3

REGION = os.environ.get("AWS_REGION", "ap-south-1")
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME", "TicketInventory")

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

kwargs = {"region_name": REGION}
if AWS_ACCESS_KEY and AWS_SECRET_KEY:
    kwargs["aws_access_key_id"] = AWS_ACCESS_KEY
    kwargs["aws_secret_access_key"] = AWS_SECRET_KEY

ddb = boto3.client('dynamodb', **kwargs)

seats = [
    {'seatId': 'PIT-01', 'tier': 'Fan Pit (VIP)', 'price': 11999},
    {'seatId': 'PIT-02', 'tier': 'Fan Pit (VIP)', 'price': 11999},
    {'seatId': 'PLT-01', 'tier': 'Platinum Lounge', 'price': 6999},
    {'seatId': 'PLT-02', 'tier': 'Platinum Lounge', 'price': 6999},
    {'seatId': 'GLD-01', 'tier': 'Gold Seating', 'price': 3499},
    {'seatId': 'GLD-02', 'tier': 'Gold Seating', 'price': 3499},
    {'seatId': 'SLV-01', 'tier': 'Silver Standing', 'price': 1499},
    {'seatId': 'SLV-02', 'tier': 'Silver Standing', 'price': 1499},
]

print(f"Resetting {len(seats)} concert seats to AVAILABLE in DynamoDB table '{TABLE_NAME}'...")

for s in seats:
    ddb.put_item(
        TableName=TABLE_NAME,
        Item={
            'PK': {'S': 'EVENT#ev-diljit-mumbai'},
            'SK': {'S': f"SEAT#{s['seatId']}"},
            'seatId': {'S': s['seatId']},
            'tier': {'S': s['tier']},
            'price': {'N': str(s['price'])},
            'status': {'S': 'AVAILABLE'},
            'currency': {'S': 'INR'}
        }
    )

print("[SUCCESS] All concert seats reset to AVAILABLE!")
