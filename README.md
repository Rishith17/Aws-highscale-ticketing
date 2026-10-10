# High-Scale AWS Concert Ticketing System

An event-driven ticket booking architecture built on AWS to handle massive flash-sale traffic spikes with zero overselling, zero database crashes, and full end-to-end CloudWatch observability.

---

## Architecture Overview

![AWS Reference Architecture](assets/aws_reference_architecture.png)

### Live 10-Layer System Preview
![Live 10-Layer System Preview](assets/live_system_preview.png)

---

## AWS 10-Layer Architecture Mapping

| Layer # | AWS Service | Role in This Application |
|:---:|:---|:---|
| **1** | **Amazon Route 53** | Global DNS routing, latency-based routing & automated health checks. |
| **2** | **Amazon CloudFront & S3** | Global CDN edge caching & static frontend asset distribution. |
| **3** | **AWS VPC & Internet Gateway** | Virtual Private Cloud network boundary isolating public & private subnets. |
| **4** | **Application Load Balancer (ALB)** | Public subnet ingress distributor, TLS termination & path routing. |
| **5** | **EC2 Auto Scaling Group (ASG)** | Private subnet backend API compute fleet (`backend-api/server.py`). |
| **6** | **Amazon RDS PostgreSQL** | Relational ACID financial database committing permanent order records. |
| **7** | **Amazon DynamoDB** | High-throughput inventory checks and **10-minute atomic conditional locks**. |
| **8** | **Amazon SQS FIFO** | Zero-loss, strictly ordered, deduplicated purchase order buffer queue. |
| **9** | **AWS Lambda (Worker)** | Async consumer worker pulling SQS batches & executing database commits. |
| **10** | **Amazon CloudWatch (Spans All Layers)** | Monitoring custom metrics (`SeatLocksAcquired`, `OrdersQueued`, `RevenueINR`) & audit logs across all layers. |

---

## Deep Dive: How ALB Works & Scales Under Surge Traffic

### 1. In the Request Path (Layer 4)
- **Public Entry Point**: Spans multiple Availability Zones to securely ingest all public API traffic.
- **Layer 7 Path Routing**: Routes `/api/*` to EC2 backend targets while CloudFront/S3 serves static assets.
- **Smart Balancing**: Uses *Least Outstanding Requests* to prevent any single server from overloading.
- **Active Health Checks**: Pings `GET /health` every 15s; ejects failing instances in < 5s.

---

### 2. How ALB Scales Itself
- **Elastic Fleet**: ALB is a managed multi-node cluster, not a single server. AWS auto-provisions balancer nodes as RPS rises.
- **Pre-Warming**: Pre-scales ALB capacity ahead of known flash sales (e.g., Diljit tour drop) for zero latency on second 1.

---

### 3. How ALB Detects Traffic Surges & Scales EC2 (Layer 5)
1. **Tracks Metrics (CloudWatch)**:
   - `RequestCountPerTarget`: Requests per healthy EC2 instance.
   - `TargetResponseTime`: Server latency in milliseconds.
2. **Triggers Auto Scaling Group (ASG)**:
   - When `RequestCountPerTarget > 500`, CloudWatch signals ASG to instantly scale out (e.g., 2 ➔ 20 instances).
3. **Zero-Downtime Traffic Handoff**:
   - New EC2 instances boot, pass health checks, and immediately absorb traffic.

---

## How It Works (Step-by-Step Ticketing Flow)

1. **Browse Live Inventory (Layer 7 DynamoDB)**:
   The user opens the web app. Available seats and pricing in ₹ INR are queried directly from **Amazon DynamoDB**.
2. **Atomic 10-Minute Hold (Layer 7 DynamoDB)**:
   Clicking a seat sends an atomic conditional update to DynamoDB:
   - If available, DynamoDB marks the seat as `LOCKED` and sets a 10-minute TTL (`lockExpiresAt`).
   - If thousands of fans click the same seat at once, only the first request succeeds; all other requests are rejected in < 5ms without touching the relational database.
   - If unpaid after 10 minutes, DynamoDB TTL automatically releases the seat back to the pool.
3. **Queue-Buffered Checkout (Layer 8 SQS FIFO)**:
   Submitting the booking sends the order payload to **Amazon SQS FIFO**:
   - SQS ensures strict First-In-First-Out ordering and deduplicates requests to prevent accidental double-charges.
   - The backend responds immediately with `202 Accepted`, protecting servers from crashing under sudden surges.
4. **Database Commit (Layer 6 RDS PostgreSQL & Layer 9 Lambda)**:
   An **AWS Lambda** worker pulls orders from the SQS queue in small, steady batches and commits the order into **Amazon RDS PostgreSQL** inside a safe transaction.
5. **Permanent Allocation (Layer 7 DynamoDB)**:
   Lambda updates the seat state in DynamoDB from `LOCKED` to permanently `SOLD`.
6. **Digital E-Ticket Pass Generation**:
   The application generates an official authenticated entry pass with unique Booking ID, allocated seat, and stadium entry QR code.
7. **Real-Time Telemetry & Monitoring (Layer 10 Amazon CloudWatch)**:
   - Emits custom metrics under the **`ConcertTicketing`** namespace: `SeatLocksAcquired`, `OrdersQueued`, and `RevenueINR`.
   - Tracks SQS backlog queue depth (`ApproximateNumberOfMessages`) in real-time to monitor buffer load.
   - Aggregates operational logs in CloudWatch Logs for audit compliance.

---

## Project Structure

```
├── assets/
│   ├── aws_reference_architecture.png   # 10-layer reference architecture diagram
│   └── live_system_preview.png          # Live verified web application screenshot
├── frontend/
│   └── index.html                       # Booking UI with 10-layer pipeline visualizer & metrics
├── backend-api/
│   ├── server.py                        # Python Boto3 API (DynamoDB + SQS FIFO + CloudWatch)
│   ├── .env                             # AWS credentials & region configuration
│   └── src/                             # Node.js alternative backend
├── lambda-order-processor/
│   ├── index.js                         # SQS FIFO consumer handler
│   └── db.js                            # RDS PostgreSQL ACID transaction
├── terraform-simple/
│   └── main.tf                          # All-in-one single-file Terraform script
└── scripts/
    ├── setup_aws_cloud.py               # Instant cloud provisioning script
    ├── reset_seats.py                   # Restock & reset all concert seats in DynamoDB
    └── process_orders_worker.py         # SQS FIFO order queue processor
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

### 5. Open the Web Application
Open `http://localhost:8080/` in any browser to experience:
- Live 10-Layer Architecture Pipeline Status.
- Real-time seat inventory from AWS DynamoDB.
- 10-minute atomic locks with DynamoDB `ConditionExpression`.
- Purchases dispatched to Amazon SQS FIFO.
- Live **CloudWatch Metrics** (`SeatLocksAcquired`, `OrdersQueued`, `RevenueINR`, `SQS Queue Depth`).
