FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

ENV PYTHONUNBUFFERED=1
ENV DEMO_MODE=0

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
