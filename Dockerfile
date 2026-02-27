FROM python:3.11-slim

# Install system dependencies needed for Prophet
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY forecasting_engine.py .

# Copy Streamlit config
COPY .streamlit .streamlit

# Copy sample files explicitly
# COPY sample_historical_data.xlsx ./
# COPY sample_actuals_2026.xlsx ./

# Create data directory
RUN mkdir -p /app/data

# Expose Streamlit default port
EXPOSE 8501

# Run Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
