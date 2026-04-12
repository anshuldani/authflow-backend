FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for sentence-transformers + chromadb
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory for ChromaDB
RUN mkdir -p data/chroma_db data/payer_policies

# Expose port (Railway + Cloud Run use $PORT env var)
EXPOSE 8001

# Start server
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8001}"]
