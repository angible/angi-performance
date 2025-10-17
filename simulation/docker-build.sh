#!/bin/bash
# Build script for RTSP Simulator Docker image

set -e

echo "Building RTSP Simulator Docker image..."
docker build -t rtsp-simulator:latest .

echo ""
echo "Build complete!"
echo ""
echo "Quick start commands:"
echo ""
echo "# Run with Docker Compose (includes MediaMTX):"
echo "docker-compose up -d"
echo ""
echo "# Run single camera manually:"
echo "docker run --rm -v \$(pwd)/cam1:/app/videos:ro --network host rtsp-simulator:latest \\"
echo "  --cam cam1 --video /app/videos/output.mp4 \\"
echo "  --rtsp-url rtsp://localhost:8554/cam1 \\"
echo "  --api-url http://localhost:3501/v1"
echo ""
echo "# View help:"
echo "docker run --rm rtsp-simulator:latest --help"
