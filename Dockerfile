# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for ChromaDB and building sentence-transformers
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create directories for persistent storage
RUN mkdir -p /app/data /app/chroma_db

# Copy project files
COPY src/ /app/src/
COPY static/ /app/static/
# We do not copy data/ or chroma_db/ to avoid overwriting the persistent volume
# but we will need to copy the initial sqlite DB if it's our source of truth.
COPY colognes_basenotes.db /app/

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
