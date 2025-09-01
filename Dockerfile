# Use Python 3.9 as base image (matching Pipfile requirements)
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application
COPY . .

# Install the package in development mode
RUN pip install -e .

# Create a non-root user
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Expose port 8000 (gunicorn default)
EXPOSE 8000

# Set environment variables
ENV FLASK_APP=openbadges.verifier.server.app
ENV PYTHONPATH=/app

# Use gunicorn for production serving
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "openbadges.verifier.server.app:app"]
