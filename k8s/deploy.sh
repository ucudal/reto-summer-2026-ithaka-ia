#!/bin/bash

# Script para desplegar la aplicación en Kubernetes
# Deployment script for Kubernetes

set -e

echo "🚀 Desplegando Ithaka Backend en Kubernetes..."

# 1. Crear namespace
echo "📁 Creando namespace..."
kubectl apply -f k8s/namespace.yaml

# 2. Crear secret para ACR
echo "🔐 Creando secret para Azure Container Registry..."
kubectl create secret docker-registry acr-secret \
  --namespace=ithaka-backend \
  --docker-server=REGISTRY_URL \
  --docker-username=REGISTRY_USERNAME \
  --docker-password=REGISTRY_PASSWORD \
  --dry-run=client -o yaml | kubectl apply -f -

# 3. Crear ConfigMap
echo "⚙️  Creando ConfigMap..."
kubectl apply -f k8s/configmap.yaml

# 4. Crear Deployment
echo "🚢 Creando Deployment..."
kubectl apply -f k8s/deployment.yaml

# 5. Crear Service
echo "🔗 Creando Service..."
kubectl apply -f k8s/service.yaml

# 6. Crear ApisixRoute
echo "🌐 Creando ApisixRoute..."
kubectl apply -f k8s/apisix-route.yaml

# 7. Crear HPA
echo "📈 Creando HPA..."
kubectl apply -f k8s/hpa.yaml

echo ""
echo "✅ Deployment completado!"
echo ""
echo "🌍 Tu aplicación estará disponible en:"
echo "   https://ithaka-backend.reto-ucu.net"
echo ""
echo "📊 Para verificar el estado:"
echo "   kubectl get all -n ithaka-backend"
echo ""
echo "📋 Para ver logs:"
echo "   kubectl logs -f deployment/ithaka-backend-deployment -n ithaka-backend"
