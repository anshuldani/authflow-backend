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

# Pre-download the embedding model so it's baked into the image
# (avoids downloading 90MB at container startup on Railway)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy application code
COPY . .

# Create data directory for ChromaDB
RUN mkdir -p data/chroma_db data/payer_policies

# Expose port (Railway + Cloud Run use $PORT env var)
EXPOSE 8001

# Start server
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8001}"]
