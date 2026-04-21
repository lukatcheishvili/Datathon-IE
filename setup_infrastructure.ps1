# ── 1. GENERATE UNIQUE IDENTIFIERS ─────────────────────────────────────────────
$RANDOM_ID = Get-Random -Minimum 1000 -Maximum 9999
$PROJECT_ID = "datathon-ie-luka-$RANDOM_ID"
$BUCKET_NAME = "datathon-raw-data-$RANDOM_ID"
$REGION = "europe-west1"

Write-Host "🚀 INITIALIZING GCP INFRASTRUCTURE..." -ForegroundColor Cyan

# ── 2. CREATE GCP PROJECT ──────────────────────────────────────────────────────
Write-Host "Creating Project: $PROJECT_ID..." -ForegroundColor Yellow
gcloud projects create $PROJECT_ID --name="Datathon IE Luka" --set-as-default

# Link Billing (This assumes you have at least one billing account set up)
$BILLING_ACCOUNT = gcloud billing accounts list --format="value(name)" --limit=1
if ($BILLING_ACCOUNT) {
    Write-Host "Linking billing account: $BILLING_ACCOUNT"
    gcloud billing projects link $PROJECT_ID --billing-account=$BILLING_ACCOUNT
} else {
    Write-Host "⚠️ No billing account found. You must link one manually at https://console.cloud.google.com/billing/projects" -ForegroundColor Red
}

# ── 3. ENABLE STORAGE API ─────────────────────────────────────────────────────
Write-Host "Enabling Google Cloud Storage API..."
gcloud services enable storage.googleapis.com

# ── 4. CREATE BUCKET ─────────────────────────────────────────────────────────
Write-Host "Creating Bucket: $BUCKET_NAME..." -ForegroundColor Yellow
gcloud storage buckets create gs://$BUCKET_NAME --project=$PROJECT_ID --location=$REGION 

# Set public access
gsutil iam ch allUsers:objectViewer gs://$BUCKET_NAME

# ── 5. UPLOAD DATA (USING MULTI-THREADED UPLOAD) ──────────────────────────────
Write-Host "Uploading raw data..." -ForegroundColor Yellow
gsutil -m cp -r ./1data/* gs://$BUCKET_NAME/raw/

# ── 6. GITHUB LOGIC (Update working.ipynb BASE_URL) ───────────────────────────
$PUBLIC_URL = "https://storage.googleapis.com/$BUCKET_NAME/raw"
Write-Host "`n✅ SETUP COMPLETE" -ForegroundColor Green
Write-Host "GCP PUBLIC BASE URL: $PUBLIC_URL" -ForegroundColor Magenta
Write-Host "PASTE THIS URL INTO YOUR working.ipynb"
