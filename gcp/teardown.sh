#!/usr/bin/env bash
#
# AI Nurse — GCP teardown script
# Removes all deployed resources to stop billing.
#
# Usage:
#   chmod +x gcp/teardown.sh
#   ./gcp/teardown.sh my-project
#
set -euo pipefail

REGION="us-central1"
SERVICE_NAME="ai-nurse-api"
DB_INSTANCE="ai-nurse-db"
REDIS_INSTANCE="ai-nurse-redis"
REPO_NAME="ai-nurse"
VPC_CONNECTOR="ai-nurse-connector"

if [ -n "${1:-}" ]; then
    PROJECT_ID="$1"
else
    echo "Enter your GCP project ID:"
    read -r PROJECT_ID
fi

if [ -z "$PROJECT_ID" ]; then
    echo "ERROR: Project ID is required."
    exit 1
fi

gcloud config set project "$PROJECT_ID"

echo ""
echo "========================================="
echo "  AI Nurse — GCP Teardown"
echo "========================================="
echo "  Project:  $PROJECT_ID"
echo ""
echo "  This will DELETE:"
echo "    - Cloud Run service"
echo "    - Cloud SQL instance (and all data)"
echo "    - Memorystore Redis instance"
echo "    - VPC connector"
echo "    - Secrets"
echo "    - Artifact Registry repo"
echo "========================================="
echo ""
read -p "Are you sure? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo ">>> Deleting Cloud Run service..."
gcloud run services delete "$SERVICE_NAME" --region="$REGION" --quiet 2>/dev/null || echo "    Already deleted."

echo ">>> Deleting Cloud SQL instance..."
gcloud sql instances delete "$DB_INSTANCE" --quiet 2>/dev/null || echo "    Already deleted."

echo ">>> Deleting Memorystore Redis..."
gcloud redis instances delete "$REDIS_INSTANCE" --region="$REGION" --quiet 2>/dev/null || echo "    Already deleted."

echo ">>> Deleting VPC connector..."
gcloud compute networks vpc-access connectors delete "$VPC_CONNECTOR" --region="$REGION" --quiet 2>/dev/null || echo "    Already deleted."

echo ">>> Deleting secrets..."
for secret in ai-nurse-database-url ai-nurse-jwt-secret ai-nurse-redis-url ai-nurse-anthropic-key; do
    gcloud secrets delete "$secret" --quiet 2>/dev/null || true
done

echo ">>> Deleting Artifact Registry repo..."
gcloud artifacts repositories delete "$REPO_NAME" --location="$REGION" --quiet 2>/dev/null || echo "    Already deleted."

echo ""
echo "========================================="
echo "  Teardown complete. All resources removed."
echo "========================================="
