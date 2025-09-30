# Multi-stage build pour Niamoto avec frontend
FROM node:20-alpine AS frontend-builder

# Clone Niamoto and build frontend
WORKDIR /build
RUN apk add --no-cache git
RUN git clone --depth 1 --branch feat/pipeline-editor-unified https://github.com/niamoto/niamoto.git .

# Build React frontend
WORKDIR /build/src/niamoto/gui/ui
RUN npm ci
RUN npm run build

# Python runtime stage
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

# Clone Niamoto repository
RUN git clone --depth 1 --branch feat/pipeline-editor-unified https://github.com/niamoto/niamoto.git /tmp/niamoto

# Copy built frontend from builder stage
COPY --from=frontend-builder /build/src/niamoto/gui/ui/dist /tmp/niamoto/src/niamoto/gui/ui/dist

# Install Niamoto from local clone (with built frontend)
RUN pip install --no-cache-dir /tmp/niamoto && rm -rf /tmp/niamoto

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