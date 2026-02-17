FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    curl \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Add missing pydantic-settings if not in requirements (it was used in config.py)
RUN pip install pydantic-settings

# Copy app code
COPY . .

# Ensure data directories exist
RUN mkdir -p /app/data/thumbnails /app/data/previews /app/files

EXPOSE 8001

# Run with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
