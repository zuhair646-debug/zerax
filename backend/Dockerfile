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

COPY requirements.txt .
RUN pip install --no-cache-dir --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/ -r requirements.txt

COPY . .

EXPOSE 8080

CMD uvicorn server:app --host 0.0.0.0 --port ${PORT:-8080}
