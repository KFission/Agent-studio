#!/usr/bin/env bash
# JAI Agent OS — GKE Deployment Script
# Usage: ./k8s/deploy.sh <PROJECT_ID> <REGION> <CLUSTER_NAME>
set -euo pipefail

PROJECT_ID="${1:?Usage: deploy.sh <PROJECT_ID> <REGION> <CLUSTER_NAME>}"
REGION="${2:-us-central1}"
CLUSTER="${3:-jai-agent-os-cluster}"
TAG="${TAG:-latest}"

echo "=== JAI Agent OS — GKE Deployment ==="
echo "Project: $PROJECT_ID | Region: $REGION | Cluster: $CLUSTER"

# 1. Authenticate & set project
gcloud config set project "$PROJECT_ID"
gcloud container clusters get-credentials "$CLUSTER" --region "$REGION"

# 2. Build & push images
echo "--- Building backend image ---"
docker build -f Dockerfile.backend -t "gcr.io/$PROJECT_ID/jai-agent-os-backend:$TAG" .
docker push "gcr.io/$PROJECT_ID/jai-agent-os-backend:$TAG"

echo "--- Building frontend image ---"
docker build -f Dockerfile.frontend \
  --build-arg NEXT_PUBLIC_API_URL="https://agent-os.example.com" \
  -t "gcr.io/$PROJECT_ID/jai-agent-os-frontend:$TAG" .
docker push "gcr.io/$PROJECT_ID/jai-agent-os-frontend:$TAG"

# 3. Replace PROJECT_ID placeholders in manifests
echo "--- Applying Kubernetes manifests ---"
for f in k8s/*.yaml; do
  sed "s/PROJECT_ID/$PROJECT_ID/g" "$f" | kubectl apply -f -
done

# 4. Wait for rollout
echo "--- Waiting for backend rollout ---"
kubectl rollout status deployment/jai-backend -n jai-agent-os --timeout=300s

echo "--- Waiting for frontend rollout ---"
kubectl rollout status deployment/jai-frontend -n jai-agent-os --timeout=300s

# 5. Show status
echo ""
echo "=== Deployment Complete ==="
kubectl get pods -n jai-agent-os
kubectl get hpa -n jai-agent-os
kubectl get ingress -n jai-agent-os

echo ""
echo "Backend:  kubectl port-forward svc/jai-backend 8080:8080 -n jai-agent-os"
echo "Frontend: kubectl port-forward svc/jai-frontend 3000:3000 -n jai-agent-os"
echo "Ingress IP: kubectl get ingress jai-ingress -n jai-agent-os -o jsonpath='{.status.loadBalancer.ingress[0].ip}'"
