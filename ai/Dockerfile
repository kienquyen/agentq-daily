FROM python:3.11-slim

# Install libgomp1 (required by LightGBM) + basic build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (cached layer — only rebuilds if requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium with all system dependencies
RUN playwright install --with-deps chromium

# Copy the rest of the application
COPY . .

CMD ["python", "main.py"]
