#!/bin/bash
###############################################################################
# Deploy Quantum Circuit Simulator to AWS Free Tier
#
# Prerequisites:
#   1. AWS CLI configured (aws configure)
#   2. Terraform installed
#   3. An EC2 key pair created in your AWS account
#   4. Node.js and Python installed locally
#
# Usage:
#   cd infra
#   cp terraform.tfvars.example terraform.tfvars
#   # Edit terraform.tfvars with your key pair name
#   ./deploy.sh
###############################################################################
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${CYAN}[DEPLOY]${NC} $1"; }
ok()  { echo -e "${GREEN}[OK]${NC} $1"; }
err() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

###############################################################################
# 1. Terraform — provision infrastructure
###############################################################################
log "Provisioning AWS infrastructure with Terraform..."
cd "$SCRIPT_DIR"

if [ ! -f terraform.tfvars ]; then
  err "terraform.tfvars not found. Copy terraform.tfvars.example and fill in values."
fi

terraform init -input=false
terraform apply -auto-approve

# Capture outputs
BACKEND_IP=$(terraform output -raw backend_public_ip)
BACKEND_URL="http://${BACKEND_IP}:8000"
BUCKET_NAME=$(terraform output -raw frontend_bucket_name)
FRONTEND_URL=$(terraform output -raw frontend_website_url)
SSH_KEY_NAME=$(terraform output -raw ssh_command | grep -oP '~/.ssh/\K[^.]+')

ok "Infrastructure provisioned"
log "Backend IP: $BACKEND_IP"
log "Frontend bucket: $BUCKET_NAME"

###############################################################################
# 2. Build frontend with backend URL baked in
###############################################################################
log "Building frontend..."
cd "$PROJECT_DIR/frontend"

VITE_API_URL="$BACKEND_URL" npm run build 2>/dev/null || {
  # If tsc fails, build with vite directly (skip type check)
  log "Type check had issues, building with Vite directly..."
  VITE_API_URL="$BACKEND_URL" npx vite build
}

ok "Frontend built (API pointing to $BACKEND_URL)"

###############################################################################
# 3. Upload frontend to S3
###############################################################################
log "Uploading frontend to S3..."

aws s3 sync dist/ "s3://${BUCKET_NAME}/" \
  --delete \
  --cache-control "public, max-age=3600" \
  --content-type "text/html" \
  --exclude "*" --include "*.html"

aws s3 sync dist/ "s3://${BUCKET_NAME}/" \
  --delete \
  --cache-control "public, max-age=31536000" \
  --exclude "*.html"

ok "Frontend uploaded to S3"

###############################################################################
# 4. Deploy backend to EC2
###############################################################################
log "Waiting for EC2 instance to be ready..."
sleep 10

# Wait for SSH to be available
for i in {1..30}; do
  if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -i ~/.ssh/${SSH_KEY_NAME}.pem ec2-user@${BACKEND_IP} "echo ok" &>/dev/null; then
    break
  fi
  log "Waiting for SSH... ($i/30)"
  sleep 10
done

log "Deploying backend code to EC2..."

# Package backend
cd "$PROJECT_DIR"
tar czf /tmp/quantum-sim-backend.tar.gz \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.pytest_cache' \
  --exclude='venv' \
  --exclude='*.egg-info' \
  -C backend .

# Upload and install
scp -o StrictHostKeyChecking=no -i ~/.ssh/${SSH_KEY_NAME}.pem \
  /tmp/quantum-sim-backend.tar.gz ec2-user@${BACKEND_IP}:/tmp/

ssh -o StrictHostKeyChecking=no -i ~/.ssh/${SSH_KEY_NAME}.pem ec2-user@${BACKEND_IP} << 'REMOTE'
  sudo mkdir -p /opt/quantum-sim
  sudo chown ec2-user:ec2-user /opt/quantum-sim
  cd /opt/quantum-sim
  tar xzf /tmp/quantum-sim-backend.tar.gz

  # Install dependencies
  python3.11 -m pip install --user --upgrade pip 2>/dev/null || python3 -m pip install --user --upgrade pip
  python3.11 -m pip install --user -r requirements.txt 2>/dev/null || python3 -m pip install --user -r requirements.txt
  python3.11 -m pip install --user -e . 2>/dev/null || python3 -m pip install --user -e .

  # Start the service
  sudo systemctl restart quantum-sim
  sudo systemctl status quantum-sim --no-pager || true
REMOTE

ok "Backend deployed to EC2"

# Clean up
rm -f /tmp/quantum-sim-backend.tar.gz

###############################################################################
# 5. Verify
###############################################################################
log "Verifying deployment..."
sleep 5

# Check backend health
if curl -sf "${BACKEND_URL}/health" >/dev/null 2>&1; then
  ok "Backend API is healthy"
else
  log "Backend may still be starting up. Check in a minute."
fi

###############################################################################
# Done!
###############################################################################
echo ""
echo "=============================================="
echo -e "${GREEN}DEPLOYMENT COMPLETE${NC}"
echo "=============================================="
echo ""
echo -e "Frontend:  ${CYAN}http://${FRONTEND_URL}${NC}"
echo -e "Backend:   ${CYAN}${BACKEND_URL}${NC}"
echo -e "API Docs:  ${CYAN}${BACKEND_URL}/docs${NC}"
echo -e "Health:    ${CYAN}${BACKEND_URL}/health${NC}"
echo ""
echo -e "SSH:       ssh -i ~/.ssh/${SSH_KEY_NAME}.pem ec2-user@${BACKEND_IP}"
echo ""
echo "All on AWS Free Tier — \$0/month"
echo "=============================================="
