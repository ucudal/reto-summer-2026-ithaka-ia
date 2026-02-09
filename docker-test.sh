#!/bin/bash

# Script para construir y probar la imagen Docker localmente
# Local Docker build and test script

set -e

# Variables
IMAGE_NAME="ithaka-backend"
CONTAINER_NAME="ithaka-backend-test"
PORT=8000

echo "🐳 Building Docker image..."
docker build -t $IMAGE_NAME:local .

echo "🧹 Cleaning up any existing container..."
docker rm -f $CONTAINER_NAME 2>/dev/null || true

echo "🚀 Running container..."
docker run -d \
  --name $CONTAINER_NAME \
  -p $PORT:8000 \
  -e DATABASE_URL=sqlite+aiosqlite:///./app.db \
  $IMAGE_NAME:local

echo "⏳ Waiting for application to start..."
sleep 15

echo "🔍 Testing application health..."
if curl -f http://localhost:$PORT/; then
  echo "✅ Application is running successfully!"
  echo "📱 Access the API at: http://localhost:$PORT"
  echo "📚 API docs at: http://localhost:$PORT/docs"
else
  echo "❌ Application failed to start properly"
  echo "📋 Container logs:"
  docker logs $CONTAINER_NAME
  exit 1
fi

echo ""
echo "🎯 Container is running. Use the following commands:"
echo "  Stop container: docker stop $CONTAINER_NAME"
echo "  View logs: docker logs $CONTAINER_NAME"
echo "  Remove container: docker rm -f $CONTAINER_NAME"
echo "  Remove image: docker rmi $IMAGE_NAME:local"
