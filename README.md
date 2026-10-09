# High-Scale AWS Concert Ticketing System

An event-driven ticket booking architecture built on AWS to handle massive flash-sale traffic spikes with zero overselling, zero database crashes, and full end-to-end CloudWatch observability.

---

## How It Works (Step-by-Step)

1. **Browse Live Inventory**: The user opens the web app. Available seats and pricing in ₹ INR are queried directly from **Amazon DynamoDB**.
2. **Atomic 10-Minute Hold**: Clicking a seat sends a request to the backend, which executes an atomic conditional lock in DynamoDB:
   - If available, DynamoDB marks the seat as `LOCKED` and sets a 10-minute TTL (`lockExpiresAt`).
   - If thousands of fans click the same seat at once, only the first request succeeds; all other requests are rejected in < 5ms without touching the database.
   - If unpaid after 10 minutes, DynamoDB TTL automatically releases the seat back to the pool.
3. **Queue-Buffered Checkout**: Submitting the booking sends the order payload to **Amazon SQS FIFO**:
   - SQS ensures strict First-In-First-Out processing and deduplicates requests to prevent accidental double-charges.
   - The backend responds immediately with `202 Accepted`, protecting servers from crashing under sudden surges.
4. **Database Commit (ACID)**: An **AWS Lambda** worker pulls orders from the SQS queue in small, steady batches and commits the order into **Amazon RDS PostgreSQL** inside a safe transaction.
5. **Permanent Allocation**: Lambda updates the seat state in DynamoDB from `LOCKED` to permanently `SOLD`.
6. **E-Ticket Delivery**: Lambda invokes **Amazon SES** to send an official confirmation email containing the attendee pass and entry QR code.
7. **Real-Time Telemetry & Monitoring (Layer 10: Amazon CloudWatch)**:
   - Emits custom metrics under the **`ConcertTicketing`** namespace: `SeatLocksAcquired`, `OrdersQueued`, and `RevenueINR`.
   - Tracks SQS backlog queue depth (`ApproximateNumberOfMessages`) in real-time to alert on demand surges.
   - Aggregates operational logs in CloudWatch Logs for audit compliance.

---

## Architecture Flow

```
[Customer Browser]
       │
       ▼ (1) Click Seat (e.g. Fan Pit, ₹11,999)
[Backend API (EC2 / Local)]
       │
       ▼ (2) Atomic Conditional Lock (10-minute hold with TTL)
[Amazon DynamoDB (TicketInventory)]
       │
       ▼ (3) Submit Order
[Backend API]
       │
       ▼ (4) Enqueue Order with Deduplication
[Amazon SQS FIFO (ticket-purchases.fifo)]
       │
       ▼ (5) Pull Batch
[AWS Lambda (Worker)]
       ├──► (6) Commit ACID Transaction (RDS PostgreSQL)
       ├──► (7) Mark Seat Status as "SOLD" (DynamoDB)
       └──► (8) Send E-Ticket with QR Code (Amazon SES)

═════════════════════════════════════════════════════════════════════════════════════
  [Layer 10: Amazon CloudWatch Monitoring & Metrics (Namespace: ConcertTicketing)]
   • SeatLocksAcquired  • OrdersQueued  • RevenueINR (₹)  • SQS FIFO Queue Depth
═════════════════════════════════════════════════════════════════════════════════════
```

---

## Why This Architecture?

- **DynamoDB Atomic Locks**: Absorbs massive click-rushes at the edge without putting heavy query load on relational databases.
- **SQS FIFO Queue**: Acts as a shock absorber so 50,000 simultaneous checkouts don't crash backend services.
- **RDS PostgreSQL**: Keeps ACID-compliant financial receipts, user accounts, and permanent order records.
- **Amazon CloudWatch**: Gives full visibility into business metrics (`RevenueINR`, `SeatLocksAcquired`) and system health (queue backlog).
- **VPC Subnet Isolation**: Backend and databases live securely in private subnets with no public internet exposure.

---

## Project Structure

```
├── frontend/
│   └── index.html               # Booking UI with live CloudWatch metrics & event stream
├── backend-api/
│   ├── server.py                # Python Boto3 API (DynamoDB + SQS FIFO + CloudWatch metrics)
│   ├── .env                     # AWS credentials & region configuration
│   └── src/                     # Node.js alternative backend
├── lambda-order-processor/
│   ├── index.js                 # SQS FIFO consumer handler
│   ├── db.js                    # RDS PostgreSQL ACID transaction
│   └── emailService.js          # Amazon SES ticket dispatcher
├── terraform-simple/
│   └── main.tf                  # All-in-one single-file Terraform script
└── scripts/
    └── setup_aws_cloud.py       # Instant cloud provisioning script
```

---

## Quickstart (Run with Real AWS)

### 1. Prerequisites
- Python 3.10+
- AWS Account with an IAM Access Key

### 2. Configure Credentials
Edit `backend-api/.env`:
```env
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
DYNAMODB_TABLE_NAME=TicketInventory
SQS_QUEUE_URL=https://sqs.ap-south-1.amazonaws.com/<account-id>/ticket-purchases.fifo
```

### 3. Provision AWS Resources (DynamoDB & SQS)
```bash
python scripts/setup_aws_cloud.py
```

### 4. Start the Backend Server
```bash
cd backend-api
python server.py
```
Server runs on `http://localhost:8080`.

### 5. Open the Frontend
Open `frontend/index.html` in any web browser. You will see:
- Real-time seat inventory loaded from AWS DynamoDB.
- 10-minute atomic locks executed with DynamoDB `ConditionExpression`.
- Purchases dispatched to Amazon SQS FIFO.
- Live **CloudWatch Metrics** (`SeatLocksAcquired`, `OrdersQueued`, `RevenueINR`).
