###############################################################################
# Quantum Circuit Simulator — AWS Free Tier Deployment
#
# Architecture:
#   Frontend → S3 static website + CloudFront CDN
#   Backend  → EC2 t2.micro (750 hrs/month free for 12 months)
#   Redis    → None (uses in-memory fallback already built into the app)
#
# Cost: $0 on AWS Free Tier (first 12 months)
#   - EC2 t2.micro: 750 hrs/month free
#   - S3: 5 GB storage + 20k GET requests free
#   - CloudFront: 1 TB transfer/month free (12 months)
#   - Data transfer: 15 GB/month free
###############################################################################

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

###############################################################################
# Variables
###############################################################################

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "quantum-circuit-sim"
}

variable "ssh_key_name" {
  description = "Name of an existing EC2 Key Pair for SSH access"
  type        = string
}

variable "my_ip" {
  description = "Your IP for SSH access (e.g. 1.2.3.4/32). Use 0.0.0.0/0 if unsure."
  type        = string
  default     = "0.0.0.0/0"
}

###############################################################################
# Data Sources
###############################################################################

# Latest Amazon Linux 2023 AMI (free tier eligible)
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

data "aws_caller_identity" "current" {}

###############################################################################
# Networking — Default VPC (free, already exists)
###############################################################################

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

###############################################################################
# Security Group for EC2 Backend
###############################################################################

resource "aws_security_group" "backend" {
  name_prefix = "${var.project_name}-backend-"
  description = "Allow HTTP and SSH to backend"
  vpc_id      = data.aws_vpc.default.id

  # SSH
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip]
    description = "SSH access"
  }

  # Backend API
  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Backend API"
  }

  # Outbound
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-backend-sg"
  }
}

###############################################################################
# EC2 Instance — Backend API (t2.micro = Free Tier)
###############################################################################

resource "aws_instance" "backend" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t2.micro" # FREE TIER
  key_name               = var.ssh_key_name
  vpc_security_group_ids = [aws_security_group.backend.id]

  # 8 GB gp3 root volume (free tier: 30 GB)
  root_block_device {
    volume_size = 8
    volume_type = "gp3"
  }

  user_data = <<-USERDATA
    #!/bin/bash
    set -e

    # Install Python 3.11 and pip
    dnf update -y
    dnf install -y python3.11 python3.11-pip git

    # Create app directory
    mkdir -p /opt/quantum-sim
    cd /opt/quantum-sim

    # Clone the repo (will be replaced by deploy script)
    # For now, create a placeholder
    cat > /opt/quantum-sim/setup.sh << 'SETUP'
    #!/bin/bash
    cd /opt/quantum-sim
    python3.11 -m pip install --upgrade pip
    pip3.11 install -r requirements.txt
    pip3.11 install -e .
    SETUP
    chmod +x /opt/quantum-sim/setup.sh

    # Create systemd service for the backend
    cat > /etc/systemd/system/quantum-sim.service << 'SERVICE'
    [Unit]
    Description=Quantum Circuit Simulator API
    After=network.target

    [Service]
    Type=simple
    User=ec2-user
    WorkingDirectory=/opt/quantum-sim
    ExecStart=/usr/bin/python3.11 -m uvicorn quantum_simulator.api.main:app --host 0.0.0.0 --port 8000
    Restart=always
    RestartSec=5
    Environment=REDIS_URL=

    [Install]
    WantedBy=multi-user.target
    SERVICE

    systemctl daemon-reload
    systemctl enable quantum-sim
  USERDATA

  tags = {
    Name = "${var.project_name}-backend"
  }
}

###############################################################################
# S3 Bucket — Frontend Static Site (Free Tier: 5 GB, 20k requests)
###############################################################################

resource "aws_s3_bucket" "frontend" {
  bucket_prefix = "${var.project_name}-frontend-"
  force_destroy = true

  tags = {
    Name = "${var.project_name}-frontend"
  }
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_website_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "index.html"
  }
}

resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  depends_on = [aws_s3_bucket_public_access_block.frontend]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.frontend.arn}/*"
      }
    ]
  })
}

resource "aws_s3_bucket_cors_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET"]
    allowed_origins = ["*"]
    max_age_seconds = 3600
  }
}

###############################################################################
# Outputs
###############################################################################

output "backend_public_ip" {
  description = "Public IP of the backend EC2 instance"
  value       = aws_instance.backend.public_ip
}

output "backend_public_dns" {
  description = "Public DNS of the backend EC2 instance"
  value       = aws_instance.backend.public_dns
}

output "backend_api_url" {
  description = "Backend API URL"
  value       = "http://${aws_instance.backend.public_ip}:8000"
}

output "frontend_website_url" {
  description = "Frontend S3 website URL"
  value       = aws_s3_bucket_website_configuration.frontend.website_endpoint
}

output "frontend_bucket_name" {
  description = "S3 bucket name for frontend deployment"
  value       = aws_s3_bucket.frontend.id
}

output "ssh_command" {
  description = "SSH command to connect to backend"
  value       = "ssh -i ~/.ssh/${var.ssh_key_name}.pem ec2-user@${aws_instance.backend.public_ip}"
}
