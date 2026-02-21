FROM python:3.11-slim

# Install system dependencies for Prophet
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY forecasting_engine.py .
COPY sample_*.xlsx ./
COPY .streamlit .streamlit

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 8501

# Healthcheck using Streamlit's actual health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Run Streamlit
CMD ["./start.sh"]
