# ---------- 1. Frontend build ----------
FROM node:20-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---------- 2. Runtime: FastAPI + bot + (optional) embedded PostgreSQL ----------
FROM python:3.11-slim
# EMBEDDED_PG=0 builds a slimmer image for use with a managed DATABASE_URL (e.g. Railway Postgres).
ARG EMBEDDED_PG=1
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PGDATA=/data/postgres UPLOAD_DIR=/data/uploads FRONTEND_DIST=/app/frontend/dist
RUN if [ "$EMBEDDED_PG" = "1" ]; then \
      apt-get update \
      && apt-get install -y --no-install-recommends postgresql postgresql-contrib gosu \
      && rm -rf /var/lib/apt/lists/*; \
    fi
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=web /web/dist /app/frontend/dist
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
# Persistent storage: attach a Railway Volume at /data (VOLUME is not allowed on Railway).
EXPOSE 8000
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
