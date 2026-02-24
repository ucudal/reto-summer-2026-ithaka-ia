# Use Python 3.12 slim image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DATABASE_URL=postgresql+asyncpg://localhost:5432/ithaka_db

# Set work directory
WORKDIR /app

# Pin uv to a trusted version; bump deliberately during dependency maintenance.
ARG UV_VERSION=0.5.31
# Optional Guardrails Hub token to pre-install validators during build.
ARG GUARDRAILS_HUB_TOKEN=""

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies with uv
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Make start script executable
RUN chmod +x start.sh

# Create a non-root user
RUN adduser --disabled-password --gecos '' appuser \
    && chown -R appuser:appuser /app

# Optionally install Guardrails validators at build-time when a Hub token is provided.
RUN if [ -n "$GUARDRAILS_HUB_TOKEN" ]; then \
        guardrails configure --token "${GUARDRAILS_HUB_TOKEN}" --disable-metrics --disable-remote-inferencing; \
        guardrails hub install hub://guardrails/detect_jailbreak; \
    else \
        echo "Skipping Guardrails Hub install (provide GUARDRAILS_HUB_TOKEN build arg to enable)."; \
    fi

USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Run the application
CMD ["./start.sh"]
