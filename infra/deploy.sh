#!/bin/bash
set -e
echo "Deploying CLOUDBURNER17..."
docker build -t invariant-engine -f backend/Dockerfile .
docker stop invariant-engine || true
docker rm invariant-engine || true
docker run -d --name invariant-engine -p 8000:8000 invariant-engine
echo "Deployment complete. Verify sentinel reproducibility."
