# Deployment Guide - Free Tier

Deploy Omnibus Legal Compass using free cloud services.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Vercel        │     │    Render       │     │  Qdrant Cloud   │
│   (Frontend)    │────▶│   (Backend)     │────▶│  (Vector DB)    │
│   Next.js       │     │   FastAPI       │     │   Free 1GB      │
│   FREE          │     │   FREE          │     │   FREE          │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## Step 1: Set Up Qdrant Cloud (5 min)

1. Go to [https://cloud.qdrant.io](https://cloud.qdrant.io)
2. Sign up with GitHub/Google
3. Click **"Create Cluster"**
   - Name: `omnibus-legal`
   - Cloud: AWS
   - Region: `ap-southeast-1` (Singapore - closest to Indonesia)
   - Plan: **Free** (1GB storage)
4. Wait for cluster to be ready (~2 min)
5. Copy your credentials:
   - **Cluster URL**: `https://xxxxx.aws.cloud.qdrant.io:6333`
   - **API Key**: Click "API Keys" → Create new key → Copy

---

## Step 2: Ingest Data to Qdrant Cloud (Local)

Before deploying, ingest your legal documents to Qdrant Cloud:

```bash
# Set environment variables
export QDRANT_URL="https://your-cluster.aws.cloud.qdrant.io:6333"
export QDRANT_API_KEY="your-api-key-here"

# Run ingestion
cd backend
python scripts/ingest.py
```

You should see: `✅ Successfully ingested 135 documents into Qdrant`

---

## Step 3: Deploy Backend to Render (10 min)

1. Go to [https://render.com](https://render.com)
2. Sign up with GitHub
3. Click **"New +"** → **"Web Service"**
4. Connect your GitHub repo: `vaskoyudha/Regulatory-Harmonization-Engine`
5. Configure:
   - **Name**: `omnibus-legal-api`
   - **Region**: Singapore
   - **Branch**: `main`
   - **Root Directory**: (leave empty)
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free

6. Add Environment Variables:
   | Key | Value |
   |-----|-------|
   | `NVIDIA_API_KEY` | Your NVIDIA NIM API key |
   | `QDRANT_URL` | `https://your-cluster.aws.cloud.qdrant.io:6333` |
   | `QDRANT_API_KEY` | Your Qdrant Cloud API key |

7. Click **"Create Web Service"**
8. Wait for deploy (~5 min)
9. Copy your backend URL: `https://omnibus-legal-api.onrender.com`

---

## Step 4: Deploy Frontend to Vercel (5 min)

1. Go to [https://vercel.com](https://vercel.com)
2. Sign up with GitHub
3. Click **"Add New..."** → **"Project"**
4. Import: `vaskoyudha/Regulatory-Harmonization-Engine`
5. Configure:
   - **Framework Preset**: Next.js
   - **Root Directory**: `frontend`
   
6. Add Environment Variables:
   | Key | Value |
   |-----|-------|
   | `NEXT_PUBLIC_API_URL` | `https://omnibus-legal-api.onrender.com` |

7. Click **"Deploy"**
8. Wait for deploy (~2 min)
9. Your app is live at: `https://your-project.vercel.app`

---

## Environment Variables Summary

### Backend (Render)
```env
NVIDIA_API_KEY=nvapi-xxxxx
QDRANT_URL=https://your-cluster.aws.cloud.qdrant.io:6333
QDRANT_API_KEY=your-qdrant-api-key
```

### Frontend (Vercel)
```env
NEXT_PUBLIC_API_URL=https://omnibus-legal-api.onrender.com
```

---

## Free Tier Limits

| Service | Limit | Notes |
|---------|-------|-------|
| **Vercel** | 100GB bandwidth/month | Unlimited deploys |
| **Render** | 750 hours/month | Spins down after 15min inactivity, ~30s cold start |
| **Qdrant Cloud** | 1GB storage | ~10,000 documents with 384-dim embeddings |
| **NVIDIA NIM** | 1000 requests/day | Rate limited |

---

## Troubleshooting

### Backend takes long to respond
Render free tier spins down after 15 minutes of inactivity. First request after sleep takes ~30 seconds.

**Solution**: Use a cron job to ping the backend every 10 minutes, or upgrade to paid tier ($7/month).

### "Collection not found" error
You need to ingest data to Qdrant Cloud first. Run the ingestion script locally with your cloud credentials.

### CORS errors
Make sure your Render backend URL is correct in Vercel's `NEXT_PUBLIC_API_URL`.

---

## Upgrading

When you outgrow free tier:

| Service | Upgrade To | Cost |
|---------|------------|------|
| Render | Starter | $7/month (always on) |
| Qdrant Cloud | Starter | $25/month (4GB) |
| Vercel | Pro | $20/month (more bandwidth) |

---

## Quick Links

- **Qdrant Cloud**: https://cloud.qdrant.io
- **Render Dashboard**: https://dashboard.render.com
- **Vercel Dashboard**: https://vercel.com/dashboard
- **NVIDIA NIM**: https://build.nvidia.com
