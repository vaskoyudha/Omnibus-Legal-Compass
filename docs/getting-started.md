# Getting Started

Learn how to set up and run the Omnibus Legal Compass on your local machine.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Docker**: Required for running the Qdrant vector database.
- **Python 3.11+**: For the FastAPI backend.
- **Node.js 18+**: For the Next.js frontend.
- **NVIDIA NIM API Key**: Required for AI inference (Kimi K2 model). You can get one for free at [build.nvidia.com](https://build.nvidia.com/).

## Quick Start

### 1. Start Qdrant

Run the Qdrant vector database using Docker:

```bash
docker run -d --name omnibus-qdrant \
  -p 6333:6333 -p 6334:6334 \
  -v qdrant_storage:/qdrant/storage \
  qdrant/qdrant:latest
```

### 2. Backend Setup

Clone the repository and set up the Python environment:

```bash
git clone https://github.com/vaskoyudha/Omnibus-Legal-Compass.git
cd Omnibus-Legal-Compass
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Frontend Setup

Install dependencies for the frontend:

```bash
cd frontend
npm install
```

## Environment Variables

Create a `.env` file in the project root for the backend, and `.env.local` in the `frontend/` directory.

| Variable | Description | Location |
|----------|-------------|----------|
| `NVIDIA_API_KEY` | Your NVIDIA NIM API key | `.env` |
| `QDRANT_URL` | URL for Qdrant (default: `http://localhost:6333`) | `.env` |
| `NEXT_PUBLIC_API_URL` | Backend API URL (default: `http://localhost:8000`) | `frontend/.env.local` |

## First Query

Once the backend is running (`uvicorn main:app` in the `backend/` directory), you can test it with a simple curl command:

```bash
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Apa itu NIB?"}'
```
