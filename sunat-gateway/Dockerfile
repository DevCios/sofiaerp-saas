# ==============================================================================
# SOFIA SUNAT Gateway — Dockerfile (FastAPI + Celery + XMLDSig + SOAP/REST)
# Multi-stage build ligero y seguro sin privilegios root
# ==============================================================================
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libxml2-dev \
    libxslt1-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libxml2 \
    libxslt1.1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --system --gid 1001 sofia && \
    adduser --system --uid 1001 --ingroup sofia --no-create-home sofia && \
    mkdir -p /var/lib/sofia-sunat/storage && \
    chown -R sofia:sofia /var/lib/sofia-sunat

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/app"

COPY . /app
RUN chown -R sofia:sofia /app

USER sofia

EXPOSE 8010

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8010/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010", "--workers", "1"]
