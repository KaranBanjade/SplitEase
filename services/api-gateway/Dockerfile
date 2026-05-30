FROM python:3.12-slim

WORKDIR /app

# Copy and install dependencies first (layer-cache friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

EXPOSE 8000

# Run with uvicorn. Adjust --workers for production (needs gunicorn or
# multiple replicas); single worker is fine for development.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
