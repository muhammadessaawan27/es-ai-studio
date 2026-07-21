# Use official lightweight Python image
FROM python:3.11-slim

# Install system dependencies for MoviePy/FFmpeg and SQLite
RUN apt-get update && apt-get install -y \
    ffmpeg \
    sqlite3 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirement files
COPY requirements.txt .

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Command to run the application
CMD ["streamlit", "run", "App.py", "--server.port=8501", "--server.address=0.0.0.0"]
