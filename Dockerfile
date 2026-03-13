FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (git for version info, curl for health checks)
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY scripts/ scripts/
COPY data/ data/
COPY plugins/ plugins/

# Create output directories with proper permissions
RUN mkdir -p output/pipeline output/logs && chmod -R 777 output

# Set safe defaults (override with .env on container run)
ENV AUTO_UPLOAD=false
ENV SITE_TIMEZONE=America/Chicago

# Health check: verify model artifacts exist
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import os; \
    missing = []; \
    required = ['data/artifacts/event_classifier_model.pkl', 'data/artifacts/event_vectorizer.pkl']; \
    [missing.append(f) for f in required if not os.path.exists(f)]; \
    exit(0 if not missing else 1)"

# Default command: run the pipeline
CMD ["python", "scripts/automated_pipeline.py"]
