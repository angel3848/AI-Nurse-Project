#!/usr/bin/env bash
#
# AI Nurse — Full GCP deployment script
# Deploys: Cloud SQL (PostgreSQL), Memorystore (Redis), Cloud Run, Secret Manager
#
# Usage:
#   chmod +x gcp/deploy.sh
#   ./gcp/deploy.sh            # interactive — prompts for project ID
#   ./gcp/deploy.sh my-project # pass project ID as argument
#
set -euo pipefail

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
REGION="us-central1"
SERVICE_NAME="ai-nurse-api"
DB_INSTANCE="ai-nurse-db"
DB_NAME="ai_nurse"
DB_USER="ai_nurse_user"
REDIS_INSTANCE="ai-nurse-redis"
REPO_NAME="ai-nurse"
VPC_CONNECTOR="ai-nurse-connector"
VPC_NETWORK="default"

# ──────────────────────────────────────────────
# Parse project ID
# ──────────────────────────────────────────────
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

echo ""
echo "========================================="
echo "  AI Nurse — GCP Deployment"
echo "========================================="
echo "  Project:  $PROJECT_ID"
echo "  Region:   $REGION"
echo "  Service:  $SERVICE_NAME"
echo "========================================="
echo ""

gcloud config set project "$PROJECT_ID"

# ──────────────────────────────────────────────
# 1. Enable required APIs
# ──────────────────────────────────────────────
echo ">>> Enabling GCP APIs..."
gcloud services enable \
    run.googleapis.com \
    sqladmin.googleapis.com \
    redis.googleapis.com \
    secretmanager.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    vpcaccess.googleapis.com \
    compute.googleapis.com \
    --quiet

echo "    APIs enabled."

# ──────────────────────────────────────────────
# 2. Create Artifact Registry repo
# ──────────────────────────────────────────────
echo ">>> Creating Artifact Registry repository..."
if ! gcloud artifacts repositories describe "$REPO_NAME" --location="$REGION" &>/dev/null; then
    gcloud artifacts repositories create "$REPO_NAME" \
        --repository-format=docker \
        --location="$REGION" \
        --description="AI Nurse Docker images" \
        --quiet
    echo "    Repository created."
else
    echo "    Repository already exists."
fi

# ──────────────────────────────────────────────
# 3. Create Cloud SQL instance
# ──────────────────────────────────────────────
echo ">>> Creating Cloud SQL PostgreSQL instance..."
if ! gcloud sql instances describe "$DB_INSTANCE" &>/dev/null; then
    gcloud sql instances create "$DB_INSTANCE" \
        --database-version=POSTGRES_15 \
        --tier=db-f1-micro \
        --region="$REGION" \
        --storage-type=SSD \
        --storage-size=10GB \
        --availability-type=zonal \
        --no-assign-ip \
        --network="projects/$PROJECT_ID/global/networks/$VPC_NETWORK" \
        --quiet
    echo "    Cloud SQL instance created."
else
    echo "    Cloud SQL instance already exists."
fi

# Generate DB password
DB_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")

echo ">>> Creating database and user..."
gcloud sql databases create "$DB_NAME" --instance="$DB_INSTANCE" --quiet 2>/dev/null || echo "    Database already exists."
gcloud sql users create "$DB_USER" --instance="$DB_INSTANCE" --password="$DB_PASSWORD" --quiet 2>/dev/null || \
    gcloud sql users set-password "$DB_USER" --instance="$DB_INSTANCE" --password="$DB_PASSWORD" --quiet
echo "    Database user configured."

# Get Cloud SQL private IP
DB_IP=$(gcloud sql instances describe "$DB_INSTANCE" --format='value(ipAddresses[0].ipAddress)')
DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@${DB_IP}:5432/${DB_NAME}"

# ──────────────────────────────────────────────
# 4. Create Memorystore Redis instance
# ──────────────────────────────────────────────
echo ">>> Creating Memorystore Redis instance..."
if ! gcloud redis instances describe "$REDIS_INSTANCE" --region="$REGION" &>/dev/null; then
    gcloud redis instances create "$REDIS_INSTANCE" \
        --size=1 \
        --region="$REGION" \
        --redis-version=redis_7_0 \
        --network="$VPC_NETWORK" \
        --tier=basic \
        --quiet
    echo "    Redis instance created."
else
    echo "    Redis instance already exists."
fi

REDIS_IP=$(gcloud redis instances describe "$REDIS_INSTANCE" --region="$REGION" --format='value(host)')
REDIS_PORT=$(gcloud redis instances describe "$REDIS_INSTANCE" --region="$REGION" --format='value(port)')
REDIS_URL="redis://${REDIS_IP}:${REDIS_PORT}/0"

# ──────────────────────────────────────────────
# 5. Create VPC Connector (Cloud Run → Cloud SQL / Redis)
# ──────────────────────────────────────────────
echo ">>> Creating Serverless VPC Access connector..."
if ! gcloud compute networks vpc-access connectors describe "$VPC_CONNECTOR" --region="$REGION" &>/dev/null; then
    gcloud compute networks vpc-access connectors create "$VPC_CONNECTOR" \
        --region="$REGION" \
        --network="$VPC_NETWORK" \
        --range="10.8.0.0/28" \
        --min-instances=2 \
        --max-instances=3 \
        --quiet
    echo "    VPC connector created."
else
    echo "    VPC connector already exists."
fi

# ──────────────────────────────────────────────
# 6. Store secrets in Secret Manager
# ──────────────────────────────────────────────
echo ">>> Storing secrets in Secret Manager..."
JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")

store_secret() {
    local name="$1"
    local value="$2"
    if ! gcloud secrets describe "$name" &>/dev/null; then
        echo -n "$value" | gcloud secrets create "$name" --data-file=- --quiet
    else
        echo -n "$value" | gcloud secrets versions add "$name" --data-file=- --quiet
    fi
}

store_secret "ai-nurse-database-url" "$DATABASE_URL"
store_secret "ai-nurse-jwt-secret" "$JWT_SECRET"
store_secret "ai-nurse-redis-url" "$REDIS_URL"

# Anthropic API key — prompt if not already stored
if ! gcloud secrets describe "ai-nurse-anthropic-key" &>/dev/null; then
    echo ""
    echo "Enter your Anthropic API key (or press Enter to skip):"
    read -rs ANTHROPIC_KEY
    if [ -n "$ANTHROPIC_KEY" ]; then
        store_secret "ai-nurse-anthropic-key" "$ANTHROPIC_KEY"
    else
        store_secret "ai-nurse-anthropic-key" "skip"
        echo "    Skipped — AI analysis will be disabled."
    fi
else
    echo "    Anthropic key already stored."
fi
echo "    Secrets stored."

# Grant Cloud Run service account access to secrets
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

for secret in ai-nurse-database-url ai-nurse-jwt-secret ai-nurse-redis-url ai-nurse-anthropic-key; do
    gcloud secrets add-iam-policy-binding "$secret" \
        --member="serviceAccount:${SA}" \
        --role="roles/secretmanager.secretAccessor" \
        --quiet &>/dev/null
done
echo "    Secret access granted to Cloud Run SA."

# ──────────────────────────────────────────────
# 7. Build and push Docker image
# ──────────────────────────────────────────────
echo ">>> Building and pushing Docker image..."
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/ai-nurse-api:latest"

gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet 2>/dev/null

gcloud builds submit \
    --tag="$IMAGE" \
    --timeout=600 \
    --quiet

echo "    Image built and pushed."

# ──────────────────────────────────────────────
# 8. Deploy to Cloud Run
# ──────────────────────────────────────────────
echo ">>> Deploying to Cloud Run..."

CLOUD_SQL_CONNECTION="${PROJECT_ID}:${REGION}:${DB_INSTANCE}"

gcloud run deploy "$SERVICE_NAME" \
    --image="$IMAGE" \
    --region="$REGION" \
    --platform=managed \
    --port=8000 \
    --allow-unauthenticated \
    --set-env-vars="APP_ENV=production,DEBUG=false,COOKIE_SECURE=true,AI_ANALYSIS_ENABLED=true" \
    --set-secrets="DATABASE_URL=ai-nurse-database-url:latest,JWT_SECRET_KEY=ai-nurse-jwt-secret:latest,REDIS_URL=ai-nurse-redis-url:latest,ANTHROPIC_API_KEY=ai-nurse-anthropic-key:latest" \
    --vpc-connector="$VPC_CONNECTOR" \
    --add-cloudsql-instances="$CLOUD_SQL_CONNECTION" \
    --min-instances=0 \
    --max-instances=3 \
    --memory=512Mi \
    --cpu=1 \
    --timeout=300 \
    --quiet

echo "    Cloud Run deployed."

# ──────────────────────────────────────────────
# 9. Get the service URL and update CORS
# ──────────────────────────────────────────────
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region="$REGION" --format='value(status.url)')

# Update allowed origins to include the Cloud Run URL and GitHub Pages
gcloud run services update "$SERVICE_NAME" \
    --region="$REGION" \
    --update-env-vars="ALLOWED_ORIGINS=${SERVICE_URL},https://angel3848.github.io" \
    --quiet

echo ""
echo "========================================="
echo "  DEPLOYMENT COMPLETE"
echo "========================================="
echo ""
echo "  App URL:     $SERVICE_URL"
echo "  Health:      ${SERVICE_URL}/health"
echo "  API docs:    ${SERVICE_URL}/docs"
echo ""
echo "  Cloud SQL:   $DB_INSTANCE ($DB_IP)"
echo "  Redis:       $REDIS_INSTANCE ($REDIS_IP)"
echo ""
echo "  Next steps:"
echo "  1. Visit $SERVICE_URL to use the app"
echo "  2. Go to your GitHub Pages app and set"
echo "     the server URL in Settings to: $SERVICE_URL"
echo "  3. Share the QR code!"
echo ""
echo "========================================="
