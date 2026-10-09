import boto3
import time
import sys
import os

REGION = os.environ.get("AWS_REGION", "ap-south-1")
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")

# Check .env if available
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

print(f"Connecting to AWS in region {REGION}...")

kwargs = {"region_name": REGION}
if AWS_ACCESS_KEY and AWS_SECRET_KEY:
    kwargs["aws_access_key_id"] = AWS_ACCESS_KEY
    kwargs["aws_secret_access_key"] = AWS_SECRET_KEY

ddb = boto3.client('dynamodb', **kwargs)
sqs = boto3.client('sqs', **kwargs)

table_name = "TicketInventory"
existing_tables = ddb.list_tables()['TableNames']

if table_name not in existing_tables:
    print(f"Creating DynamoDB table '{table_name}' in AWS...")
    ddb.create_table(
        TableName=table_name,
        KeySchema=[
            {'AttributeName': 'PK', 'KeyType': 'HASH'},
            {'AttributeName': 'SK', 'KeyType': 'RANGE'}
        ],
        AttributeDefinitions=[
            {'AttributeName': 'PK', 'AttributeType': 'S'},
            {'AttributeName': 'SK', 'AttributeType': 'S'}
        ],
        BillingMode='PAY_PER_REQUEST'
    )
    print("Waiting for DynamoDB table to become ACTIVE...")
    waiter = ddb.get_waiter('table_exists')
    waiter.wait(TableName=table_name)
    try:
        ddb.update_time_to_live(
            TableName=table_name,
            TimeToLiveSpecification={'Enabled': True, 'AttributeName': 'lockExpiresAt'}
        )
    except Exception as e:
        pass
    print("[SUCCESS] DynamoDB table created!")
else:
    print(f"[EXISTS] DynamoDB table '{table_name}' already exists and is ACTIVE.")

# 2. Seed Initial Concert Seats into DynamoDB
print("Seeding Diljit Dosanjh concert seats into DynamoDB...")
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

for s in seats:
    ddb.put_item(
        TableName=table_name,
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
print(f"[SUCCESS] Seeded {len(seats)} seats into DynamoDB table.")

# 3. Create SQS FIFO Queue: ticket-purchases.fifo
queue_name = "ticket-purchases.fifo"
try:
    print(f"Creating SQS FIFO Queue '{queue_name}' in AWS...")
    res = sqs.create_queue(
        QueueName=queue_name,
        Attributes={
            'FifoQueue': 'true',
            'ContentBasedDeduplication': 'true',
            'VisibilityTimeout': '60'
        }
    )
    queue_url = res['QueueUrl']
    print(f"[SUCCESS] SQS FIFO Queue created: {queue_url}")
except Exception as e:
    queue_url = sqs.get_queue_url(QueueName=queue_name)['QueueUrl']
    print(f"[EXISTS] SQS FIFO Queue URL: {queue_url}")

# Save to .env
with open('backend-api/.env', 'w') as f:
    f.write(f"""PORT=8080
AWS_REGION={REGION}
AWS_ACCESS_KEY_ID={AWS_ACCESS_KEY}
AWS_SECRET_ACCESS_KEY={AWS_SECRET_KEY}
DYNAMODB_TABLE_NAME={table_name}
SQS_QUEUE_URL={queue_url}
""")

print(f"\n[DONE] Connected to Real AWS Cloud in Mumbai ({REGION})!")
print(f"DynamoDB Table: {table_name}")
print(f"SQS FIFO Queue URL: {queue_url}")
