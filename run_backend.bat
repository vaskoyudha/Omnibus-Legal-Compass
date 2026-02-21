@echo off
set USE_DUMMY_RERANKER=1
cd /d "C:\Project Vasko\Regulatory Harmonization Engine\backend"
python -m uvicorn main:app --host 0.0.0.0 --port 8000
pause
