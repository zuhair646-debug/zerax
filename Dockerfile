# ============================================
# Stage 1: Build Frontend
# ============================================
FROM node:18-alpine AS frontend-builder

WORKDIR /frontend

# Copy frontend package files
COPY frontend/package*.json ./

# Install dependencies
RUN yarn install --frozen-lockfile

# Copy frontend source
COPY frontend/ ./

# Build frontend (output: /frontend/build)
RUN yarn build

# ============================================
# Stage 2: Backend + Serve Frontend
# ============================================
FROM python:3.11-slim

WORKDIR /app

# Install OS-level tools so the autocoder can run git/curl/etc. on production
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl ca-certificates openssh-client jq \
    && rm -rf /var/lib/apt/lists/*

# Configure default git identity (autocoder will override per-commit if needed)
RUN git config --global user.email "autocoder@zitex.com" \
    && git config --global user.name "Zitex AutoCoder" \
    && git config --global init.defaultBranch main \
    && git config --global --add safe.directory /app

# Install Python dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/ -r requirements.txt

# Copy backend code
COPY backend/ ./

# Copy frontend build from Stage 1
COPY --from=frontend-builder /frontend/build ./static/app

EXPOSE 8080

CMD uvicorn server:app --host 0.0.0.0 --port ${PORT:-8080}
