# Deployment Guide

Three paths to get Omnibus Legal Compass running: **local Docker** (fastest for dev), **cloud** (recommended for production), or **manual** (custom infrastructure).

---

## Option A: Local — One Command (Docker)

The fastest way to run the full stack locally. Requires [Docker](https://docs.docker.com/get-docker/) and a `.env` file.

```bash
# 1. Clone and configure
git clone https://github.com/vaskoyudha/Omnibus-Legal-Compass.git
cd "Omnibus-Legal-Compass"
cp .env.example .env
# Edit .env — add GITHUB_TOKEN or NVIDIA_API_KEY at minimum

# 2. Start all services (Qdrant + Backend + Frontend)
docker compose up --build

# 3. Ingest legal documents (first run only)
docker exec omnibus-backend python scripts/ingest.py
```

Services will be available at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Qdrant UI**: http://localhost:6333/dashboard

> **Note**: The first `docker compose up --build` takes ~5 minutes to build images. Subsequent starts are near-instant.

---

## Option B: Cloud Deployment (Recommended)

Free-tier stack: **Qdrant Cloud** (vector DB) → **Render** (backend) → **Vercel** (frontend).

| Service | Free Tier | Region | URL Pattern |
|---------|-----------|--------|-------------|
| Qdrant Cloud | 1 GB storage, 1 cluster | Singapore/AWS | `https://xxxx.ap-southeast-1.aws.cloud.qdrant.io` |
| Render | 750 hrs/mo, sleeps after 15min | Singapore | `https://omnibus-legal-api.onrender.com` |
| Vercel | Unlimited deploys | Auto (CDN) | `https://omnibus-legal-compass.vercel.app` |

### Step 1: Qdrant Cloud (Vector Database)

1. Sign up at [https://cloud.qdrant.io](https://cloud.qdrant.io)
2. Click **Create Cluster** → Free tier → Region: **AWS / ap-southeast-1 (Singapore)**
3. After cluster creation, note your:
   - **Cluster URL** — e.g., `https://abc123.ap-southeast-1.aws.cloud.qdrant.io`
   - **API Key** — generated under the cluster's **API Keys** tab
4. Ingest the legal documents into your cloud cluster:

```bash
# Run from repo root — replaces local Qdrant with cloud
QDRANT_URL=https://abc123.ap-southeast-1.aws.cloud.qdrant.io \
QDRANT_API_KEY=your-qdrant-api-key \
python -m backend.scripts.ingest
```

This ingests 401 document segments across 44 Indonesian regulations. Takes ~3–5 minutes.

---

### Step 2: Backend on Render (API Server)

The repo includes a `render.yaml` at the project root — Render auto-detects it.

1. Sign up at [https://render.com](https://render.com)
2. Click **New → Web Service** → **Connect a Git repository**
3. Select the `Omnibus-Legal-Compass` repo
4. Render reads `render.yaml` automatically. Verify these settings:
   - **Runtime**: Python 3.11
   - **Region**: Singapore (closest to Indonesia)
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/health`
5. Under **Environment → Environment Variables**, add the following:

| Variable | Value | Required |
|----------|-------|----------|
| `QDRANT_URL` | Your Qdrant Cloud cluster URL | ✅ Yes |
| `QDRANT_API_KEY` | Your Qdrant Cloud API key | ✅ Yes |
| `GITHUB_TOKEN` | GitHub PAT with Copilot access | ✅ One of these |
| `NVIDIA_API_KEY` | NVIDIA NIM API key | ✅ One of these |
| `ANTHROPIC_API_KEY` | Anthropic API key (Claude) | Optional |
| `OPENROUTER_API_KEY` | OpenRouter API key | Optional |
| `GROQ_API_KEY` | Groq API key | Optional |
| `GEMINI_API_KEY` | Google Gemini API key | Optional |

6. Click **Create Web Service** — Render begins the build (~3 minutes)
7. Note your Render URL: `https://your-service-name.onrender.com`

> **Free tier caveat**: Render free services spin down after 15 minutes of inactivity. The first request after sleep takes ~30 seconds (cold start). Upgrade to Starter ($7/mo) to keep it always-on.

---

### Step 3: Update CORS (Required Before Frontend Deploy)

The backend currently only allows `localhost` origins. You **must** add your Vercel URL before deploying the frontend — otherwise the browser will block all API requests with a CORS error.

Open `backend/main.py` and find the CORS middleware block around **line 781**:

```python
# backend/main.py ~line 781
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
```

Add your Vercel production URL to the `allow_origins` list:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "https://your-app.vercel.app",       # ← Add your Vercel URL
        "https://your-custom-domain.com",    # ← Add custom domain if any
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
```

Commit and push this change — Render auto-deploys on push (configured in `render.yaml` with `autoDeploy: true`).

---

### Step 4: Frontend on Vercel

1. Sign up at [https://vercel.com](https://vercel.com)
2. Click **Add New → Project** → **Import Git Repository**
3. Select `Omnibus-Legal-Compass`
4. Configure the project:
   - **Framework Preset**: Next.js (auto-detected)
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build` (default)
   - **Output Directory**: `.next` (default)
5. Under **Environment Variables**, add:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | `https://your-service-name.onrender.com` |

6. Click **Deploy** — Vercel builds and deploys in ~2 minutes
7. Note your Vercel URL: `https://your-app.vercel.app`

> **Custom domain**: Vercel supports free custom domains. Add one under **Project → Settings → Domains**, then add it to the Render CORS list (Step 3).

---

### Step 5: Verify the Deployment

Run these checks in order:

```bash
# 1. Backend health
curl https://your-service-name.onrender.com/health
# Expected: {"status": "healthy", ...}

# 2. Backend API docs (should return HTML)
open https://your-service-name.onrender.com/docs

# 3. Test a legal query end-to-end
curl -X POST https://your-service-name.onrender.com/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Apa syarat pendirian PT?"}'
# Expected: JSON with answer, citations, grounding_score

# 4. Frontend (open in browser)
open https://your-app.vercel.app
```

If the frontend cannot reach the backend, check:
1. `NEXT_PUBLIC_API_URL` in Vercel matches the Render URL exactly (no trailing slash)
2. The Vercel URL is in the `allow_origins` list in `backend/main.py`
3. Render service is not sleeping — hit `/health` first to wake it

---

## Environment Variables Reference

Full reference for all supported environment variables:

| Variable | Description | Where to Get | Required |
|----------|-------------|--------------|----------|
| `QDRANT_URL` | Qdrant connection URL | Qdrant Cloud cluster page | ✅ Production |
| `QDRANT_API_KEY` | Qdrant Cloud authentication key | Qdrant Cloud → API Keys tab | ✅ Cloud only |
| `GITHUB_TOKEN` | GitHub PAT for Copilot Chat API | [GitHub → Settings → Tokens](https://github.com/settings/tokens) | ✅ Default LLM |
| `NVIDIA_API_KEY` | NVIDIA NIM API key (Kimi K2, etc.) | [build.nvidia.com](https://build.nvidia.com) (free tier) | Alt LLM |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude models | [console.anthropic.com](https://console.anthropic.com) | Optional |
| `OPENROUTER_API_KEY` | OpenRouter key (200+ models) | [openrouter.ai/keys](https://openrouter.ai/keys) | Optional |
| `GROQ_API_KEY` | Groq key (Llama 3.3, free) | [console.groq.com](https://console.groq.com) | Optional |
| `GEMINI_API_KEY` | Google Gemini key (2.5 Flash/Pro) | [aistudio.google.com](https://aistudio.google.com/apikey) | Optional |
| `MISTRAL_API_KEY` | Mistral key | [console.mistral.ai](https://console.mistral.ai) | Optional |
| `NEXT_PUBLIC_API_URL` | Backend URL consumed by Next.js | Your Render service URL | ✅ Frontend |

**Minimum required for production**: `QDRANT_URL` + `QDRANT_API_KEY` + one LLM key (`GITHUB_TOKEN` or `NVIDIA_API_KEY`) + `NEXT_PUBLIC_API_URL`.

---

## Production Checklist

Before announcing your deployment:

- [ ] Qdrant Cloud cluster created in Singapore region
- [ ] Legal documents ingested (`python -m backend.scripts.ingest`)
- [ ] Qdrant collection has 401 segments — verify in Qdrant dashboard
- [ ] All required env vars set in Render dashboard
- [ ] Render health check passing: `GET /health` → `200 OK`
- [ ] CORS updated in `backend/main.py` with Vercel URL
- [ ] Backend redeployed after CORS change
- [ ] `NEXT_PUBLIC_API_URL` set in Vercel to Render URL
- [ ] Frontend can reach backend (test `/api/v1/ask` from browser)
- [ ] Test a legal query end-to-end — answer includes citations
- [ ] Grounding verification works (check `grounding_score` in response)

---

## CI/CD

The project auto-deploys on push:

- **Render**: `autoDeploy: true` in `render.yaml` — every push to `main` triggers a backend redeploy
- **Vercel**: Auto-deploy is enabled by default — every push to `main` redeploys the frontend
- **GitHub Actions**: `.github/workflows/ci.yml` runs 401 tests on every push; `.github/workflows/docs.yml` deploys this documentation site to GitHub Pages when `docs/` changes

> Both Render and Vercel deploy from the same `main` branch. If CI fails, consider adding branch protection rules to prevent deploying broken code.
