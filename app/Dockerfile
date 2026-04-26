# =============================================================================
# Project 04 — TRIBE v2 Neural Engagement Scorer
# Streamlit app container (local only — no GPU needed)
# =============================================================================

FROM python:3.12-slim

# Standard across all 4 projects — makes Python find modules in /app
ENV PYTHONPATH=/app

WORKDIR /app

# Install system deps
# libpq-dev is the PostgreSQL client library needed by psycopg2
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv — consistent with your other projects
RUN pip install uv

# Copy and install Python dependencies first (layer caching)
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

# Copy application code
COPY . .

# Streamlit default port
EXPOSE 8501
