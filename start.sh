#!/bin/bash

# Wait for database to be ready and create tables
echo "🔄 Iniciando aplicación..."

# Create database tables
echo "📊 Creando tablas de base de datos..."
python -m app.db.config.create_tables

if [ $? -ne 0 ]; then
    echo "❌ Error creando tablas de base de datos"
    exit 1
fi

echo "✅ Tablas creadas exitosamente"

# Start the application
echo "🚀 Iniciando servidor..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
