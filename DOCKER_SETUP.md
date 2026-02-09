# Docker y CI/CD Setup

## Archivos Creados

### 1. `Dockerfile`
- Imagen base: Python 3.12-slim
- Usuario no-root para seguridad
- Health check incluido
- Optimizado para FastAPI

### 2. `.dockerignore`
- Excluye archivos innecesarios del contexto de build
- Optimiza el tamaño de la imagen

### 3. Pipeline CI/CD

#### Azure DevOps (`.azure-pipelines/azure-pipelines.yml`)
- Trigger en ramas: DevOps, main, master
- Build y push automático al registry
- Deploy condicional solo para rama main

#### GitHub Actions (`.github/workflows/docker-build-push.yml`)
- Alternativa al pipeline de Azure DevOps
- Mismo comportamiento pero para GitHub

### 4. Scripts de Prueba
- `docker-test.sh`: Script para probar localmente
- `docker-compose.yml`: Para desarrollo con Docker Compose

## Configuración del Pipeline

### Para Azure DevOps:

1. **Crear Service Connection**:
   - Ve a Project Settings → Service connections
   - Crea una nueva conexión tipo "Docker Registry"
   - Nombre: `crretoxmas2024-connection`
   - Registry URL: `crretoxmas2024.azurecr.io`
   - Configura las credenciales del ACR

2. **Crear el Pipeline**:
   - Ve a Pipelines → New pipeline
   - Selecciona tu repositorio
   - Usa "Existing Azure Pipelines YAML file"
   - Selecciona `.azure-pipelines/azure-pipelines.yml`

### Para GitHub Actions:

1. **Configurar Secrets**:
   - Ve a Settings → Secrets and variables → Actions
   - Agrega estos secrets:
     - `ACR_USERNAME`: Username del Azure Container Registry
     - `ACR_PASSWORD`: Password del Azure Container Registry

2. **El workflow se ejecutará automáticamente** al hacer push a las ramas configuradas.

## Uso Local

### Probar con Docker:
```bash
# Ejecutar script de prueba
./docker-test.sh

# O manualmente:
docker build -t ithaka-backend .
docker run -p 8000:8000 ithaka-backend
```

### Probar con Docker Compose:
```bash
docker-compose up --build
```

## Registry

Las imágenes se subirán a: `crretoxmas2024.azurecr.io/ithaka-backend`

### Tags generados:
- `latest`: Última versión de la rama principal
- `<build-id>`: ID único del build
- `<branch-name>`: Nombre de la rama (en GitHub Actions)

## Comandos Útiles

```bash
# Pull de la imagen
docker pull crretoxmas2024.azurecr.io/ithaka-backend:latest

# Run de la imagen del registry
docker run -p 8000:8000 crretoxmas2024.azurecr.io/ithaka-backend:latest

# Ver logs del contenedor
docker logs <container-id>

# Acceder al contenedor
docker exec -it <container-id> /bin/bash
```

## URLs de la Aplicación

- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health check: http://localhost:8000/

## Notas

- El pipeline se activa con cada push a las ramas especificadas
- Solo los cambios en la rama `main` se despliegan automáticamente
- La imagen se optimiza con capas en caché para builds más rápidos
- Se incluye health check para verificar que la aplicación esté funcionando
