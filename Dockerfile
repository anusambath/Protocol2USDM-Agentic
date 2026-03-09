# Protocol2USDM — Production Dockerfile
# Multi-stage build for minimal image size

# Stage 1: Build dependencies
FROM python:3.13-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Production image
FROM python:3.13-slim AS production

LABEL maintainer="Protocol2USDM Team"
LABEL description="AI Agent-Based Clinical Protocol Extraction System"
LABEL version="1.0.0"

# Security: run as non-root
RUN groupadd -r p2u && useradd -r -g p2u -d /app -s /sbin/nologin p2u

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY agents/ ./agents/
COPY extraction/ ./extraction/
COPY core/ ./core/
COPY validation/ ./validation/
COPY enrichment/ ./enrichment/
COPY pipeline/ ./pipeline/
COPY utilities/ ./utilities/
COPY llm_providers.py .
COPY llm_config.yaml .
COPY main_v3.py .

# Create directories for output, checkpoints, logs
RUN mkdir -p /app/output /app/checkpoints /app/logs /app/input \
    && chown -R p2u:p2u /app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from agents.pipeline import ExtractionPipeline; print('ok')" || exit 1

# Environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV LOG_LEVEL=INFO
ENV MAX_WORKERS=4
ENV OUTPUT_DIR=/app/output
ENV CHECKPOINTS_DIR=/app/checkpoints

# Expose volume mounts
VOLUME ["/app/input", "/app/output", "/app/checkpoints", "/app/logs"]

USER p2u

# Default: run the pipeline CLI
ENTRYPOINT ["python", "main_v3.py"]
