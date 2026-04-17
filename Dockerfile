# ── Build stage ───────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim

LABEL org.opencontainers.image.title="tuya-mqtt-bridge"
LABEL org.opencontainers.image.description="TinyTuya → MQTT Bridge with NiceGUI"

# Non-root user for security
RUN useradd -m -u 1000 bridge
WORKDIR /app

# Copy installed packages
COPY --from=builder /install /usr/local

# Copy source
COPY app/ ./app/
COPY .env.example .env

# Data directory for SQLite (override with volume)
RUN mkdir -p /data && chown bridge:bridge /data

USER bridge

EXPOSE 8080

CMD ["python", "-m", "app.main"]
