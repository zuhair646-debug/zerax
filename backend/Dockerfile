FROM python:3.11-slim

WORKDIR /app

# Install OS-level tools so the autocoder can run git/curl/etc. on production
# Note: Chromium intentionally NOT installed here — adds 500MB+ and slows builds.
# browse_site() returns a clear "browser unavailable on this host" message if missing.
# To enable browser testing on production: add ENABLE_BROWSER=1 env var and uncomment below.
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl ca-certificates openssh-client jq gnupg build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 LTS + npm + yarn so the autocoder can lint/build the frontend
# locally inside the Railway container before pushing.
# Node ~50MB, yarn ~5MB — acceptable trade-off for full-stack capability.
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g yarn@1.22.22 \
    && rm -rf /var/lib/apt/lists/* \
    && node --version && yarn --version

# Configure default git identity (autocoder will override per-commit if needed)
RUN git config --global user.email "autocoder@zitex.com" \
    && git config --global user.name "Zitex AutoCoder" \
    && git config --global init.defaultBranch main \
    && git config --global --add safe.directory /app

COPY requirements.txt .
RUN pip install --no-cache-dir --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/ -r requirements.txt

COPY . .

# Bake the build-time commit SHA into the image so /api/version works on Railway
# (where /app is not a git repo). Railway sets RAILWAY_GIT_COMMIT_SHA at build time.
ARG RAILWAY_GIT_COMMIT_SHA=""
ARG RAILWAY_GIT_COMMIT_MESSAGE=""
ENV GIT_COMMIT=$RAILWAY_GIT_COMMIT_SHA
ENV RAILWAY_GIT_COMMIT_MESSAGE=$RAILWAY_GIT_COMMIT_MESSAGE

EXPOSE 8080

CMD uvicorn server:app --host 0.0.0.0 --port ${PORT:-8080}
