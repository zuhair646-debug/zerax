FROM python:3.11-slim

WORKDIR /app

# Install OS-level tools + Chromium for Playwright (real-browser testing by Auto-Coder)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl ca-certificates openssh-client jq \
    chromium \
    fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 \
    libatspi2.0-0 libcups2 libdbus-1-3 libdrm2 libgbm1 \
    libnspr4 libnss3 libxcomposite1 libxdamage1 libxfixes3 libxkbcommon0 libxrandr2 \
    && rm -rf /var/lib/apt/lists/*

ENV PLAYWRIGHT_CHROMIUM_PATH=/usr/bin/chromium \
    PLAYWRIGHT_BROWSERS_PATH=/usr/lib/chromium

# Configure default git identity (autocoder will override per-commit if needed)
RUN git config --global user.email "autocoder@zitex.com" \
    && git config --global user.name "Zitex AutoCoder" \
    && git config --global init.defaultBranch main \
    && git config --global --add safe.directory /app

COPY requirements.txt .
RUN pip install --no-cache-dir --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/ -r requirements.txt

COPY . .

EXPOSE 8080

CMD uvicorn server:app --host 0.0.0.0 --port ${PORT:-8080}
