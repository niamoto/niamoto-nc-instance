# Dockerfile pour déployer une instance Niamoto existante
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libgdal-dev \
    gdal-bin \
    libsqlite3-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Install Niamoto from GitHub - branche feat/pipeline-editor-unified
RUN pip install --no-cache-dir git+https://github.com/niamoto/niamoto.git@feat/pipeline-editor-unified

# Copy instance data
COPY config/ /data/config/
COPY db/ /data/db/
COPY imports/ /data/imports/
COPY exports/ /data/exports/
COPY plugins/ /data/plugins/
COPY templates/ /data/templates/

# Set working directory to data
WORKDIR /data

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/api/config/project || exit 1

# Run the GUI
CMD ["niamoto", "gui", "--host", "0.0.0.0", "--port", "8080", "--no-browser"]