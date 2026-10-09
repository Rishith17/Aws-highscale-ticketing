terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# 1. Network Layer (VPC, Subnets, IGW, NAT, VPC Endpoints, Security Groups)
module "vpc" {
  source       = "./modules/vpc"
  project_name = var.project_name
  environment  = var.environment
  vpc_cidr     = var.vpc_cidr
  aws_region   = var.aws_region
}

# 2. Database Layer (DynamoDB & Multi-AZ RDS PostgreSQL)
module "database" {
  source                = "./modules/database"
  project_name          = var.project_name
  environment           = var.environment
  private_db_subnet_ids = module.vpc.private_db_subnet_ids
  rds_security_group_id = module.vpc.rds_security_group_id
  db_password           = var.db_password
}

# 3. Messaging Layer (SQS FIFO & Dead Letter Queue)
module "messaging" {
  source       = "./modules/messaging"
  project_name = var.project_name
}

# 4. Compute Layer (ALB, Launch Template, Auto Scaling Group)
module "compute" {
  source                     = "./modules/compute"
  project_name               = var.project_name
  environment                = var.environment
  vpc_id                     = module.vpc.vpc_id
  public_subnet_ids          = module.vpc.public_subnet_ids
  private_compute_subnet_ids = module.vpc.private_compute_subnet_ids
  alb_security_group_id      = module.vpc.alb_security_group_id
  ec2_security_group_id      = module.vpc.ec2_security_group_id
  dynamodb_table_arn         = module.database.dynamodb_table_arn
  dynamodb_table_name        = module.database.dynamodb_table_name
  sqs_queue_arn              = module.messaging.queue_arn
  sqs_queue_url              = module.messaging.queue_url
  rds_host                   = module.database.rds_address
  db_name                    = "ticketdb"
  db_user                    = "dbadmin"
  db_password                = var.db_password
}

# 5. Serverless Fulfillment Worker (Lambda, SQS Trigger, SES)
module "lambda_worker" {
  source                     = "./modules/lambda_worker"
  project_name               = var.project_name
  environment                = var.environment
  aws_region                 = var.aws_region
  vpc_id                     = module.vpc.vpc_id
  private_compute_subnet_ids = module.vpc.private_compute_subnet_ids
  ec2_security_group_id      = module.vpc.ec2_security_group_id
  sqs_queue_arn              = module.messaging.queue_arn
  dynamodb_table_arn         = module.database.dynamodb_table_arn
  dynamodb_table_name        = module.database.dynamodb_table_name
  rds_host                   = module.database.rds_address
  db_name                    = "ticketdb"
  db_user                    = "dbadmin"
  db_password                = var.db_password
  ses_sender_email           = var.ses_sender_email
}

# 6. Global Edge & CDN (S3 Static Hosting, CloudFront Dual Origins, Route 53)
module "edge" {
  source             = "./modules/edge"
  project_name       = var.project_name
  environment        = var.environment
  alb_dns_name       = module.compute.alb_dns_name
  custom_domain_name = var.custom_domain_name
  route53_zone_id    = var.route53_zone_id
}
