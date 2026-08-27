#!/bin/bash
# Build script for Vercel Serverless Deployment
set -e

echo "=== [1/3] Installing Python Dependencies ==="
python3 -m pip install -r requirements.txt

echo "=== [2/3] Collecting Static Files ==="
python3 manage.py collectstatic --noinput --clear

echo "=== [3/3] Running Database Migrations (if accessible) ==="
python3 manage.py migrate --noinput || echo "Migration skipped or database unavailable at build time."

echo "=== Build Completed Successfully! ==="
