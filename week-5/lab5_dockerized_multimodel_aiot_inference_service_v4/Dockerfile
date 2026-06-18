# =============================================================================
# Stage 1: Builder — install dependencies only
# =============================================================================
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .

RUN pip install --no-cache-dir --no-compile --user -r requirements.txt && \
    rm -rf /root/.cache/pip

# =============================================================================
# Stage 2: Runtime — lean final image
# =============================================================================
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/root/.local/bin:$PATH \
    MODEL_DIR=/app/models \
    OUTPUT_DIR=/app/outputs \
    VISION_MODEL_PATH=/app/models/vision/resnet18-v1-7.onnx \
    VISION_LABELS_PATH=/app/models/vision/imagenet_classes.txt

WORKDIR /app

# Copy only user-installed packages from builder
COPY --from=builder /root/.local /root/.local

# Copy runtime source code
COPY app/ app/

# Create required directories and strip unnecessary system packages
RUN mkdir -p /app/outputs /app/models/vision && \
    find /app -type d -name __pycache__ -prune -exec rm -rf {} \; 2>/dev/null || true && \
    pip uninstall -y pip 2>/dev/null || true

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
