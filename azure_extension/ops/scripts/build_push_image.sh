#!/bin/bash
# Build and push Docker image to Azure Container Registry

set -e

# Configuration
ACR_NAME="${ACR_NAME:-acrdevafga}"
IMAGE_NAME="adaptive-finance-governance-agent"
VERSION="${VERSION:-latest}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

echo "Building Docker image..."
cd "$PROJECT_ROOT"

# Build image
docker build -t "${IMAGE_NAME}:${VERSION}" .

# Tag for ACR
docker tag "${IMAGE_NAME}:${VERSION}" "${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${VERSION}"

# Login to ACR
echo "Logging in to ACR..."
az acr login --name "${ACR_NAME}"

# Push to ACR
echo "Pushing image to ACR..."
docker push "${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${VERSION}"

echo "✅ Image pushed successfully: ${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${VERSION}"

