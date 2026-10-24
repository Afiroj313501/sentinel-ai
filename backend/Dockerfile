FROM python:3.12-slim

# Install system dependencies:
# - git (for repository scanning and tools)
# - nodejs and npm (required for npm-audit scanner)
# - curl (for health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first for layer caching
COPY backend/requirements.txt backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend application code
COPY backend/ /app/backend/

# Ensure SQLite data directory exists
RUN mkdir -p /app/backend/data

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/backend
ENV SENTINEL_ENVIRONMENT=production

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
