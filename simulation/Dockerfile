FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    iputils-ping \
    curl \
    net-tools \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-rtsp \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    libgirepository1.0-dev \
    gir1.2-gstreamer-1.0 \
    gir1.2-gst-rtsp-server-1.0 \
    libcairo2-dev \
    libglib2.0-dev \
    pkg-config \
    python3-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app
RUN apt-get update && apt-get install -y libgirepository-2.0-dev gstreamer1.0-plugins-ugly 
# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY simulation_v2.py simulation.py
COPY schemas.py .

# Copy default config (can be overridden by mounting a volume)
COPY config.yaml .

# Create directory for video files (can be mounted as volume)
RUN mkdir -p /app/videos

# Set Python to run in unbuffered mode for better logging
ENV PYTHONUNBUFFERED=1
# Force colored output in terminal
ENV FORCE_COLOR=1
ENV TERM=xterm-256color

# Use ENTRYPOINT to allow passing arguments
ENTRYPOINT ["python", "simulation.py"]

# Default CMD can be overridden
CMD ["--help"]
