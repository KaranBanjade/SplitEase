FROM python:3.12-slim

WORKDIR /app

# System libraries required by asyncpg and pywebpush
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Make /app importable as the 'app' package from the filesystem root
ENV PYTHONPATH=/

# No HTTP port – this is a worker process only
CMD ["python", "-m", "app.main"]
