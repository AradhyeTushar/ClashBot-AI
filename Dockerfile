# -----------------------------------------------------------------------------
# ClashBot AI - Multi-Tenant Cloud Container
# Author: Aradhye Tushar (https://github.com/AradhyeTushar)
# -----------------------------------------------------------------------------
FROM python:3.10-slim

# Set non-interactive mode for apt and timezone
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install required system dependencies for OpenCV, Tesseract, and Headless PySide6 (Qt)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    tesseract-ocr \
    xvfb \
    libegl1 \
    libxkbcommon-x11-0 \
    libfontconfig1 \
    libdbus-1-3 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-xinerama0 \
    libxcb-xfixes0 \
    libxcb-shape0 \
    x11-utils \
    && rm -rf /var/lib/apt/lists/*

# Set working directory for the bot
WORKDIR /app

# Copy dependency requirements and install
COPY Host/requirements.txt ./requirements.txt

# Install Python packages
# We upgrade pip and use opencv-python-headless to avoid X11 overhead for vision tasks
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip uninstall -y opencv-python && \
    pip install --no-cache-dir opencv-python-headless

# Copy the entire Host engine codebase (including PyArmor files)
COPY Host/ /app/Host/

# Set Python path to ensure imports work correctly
ENV PYTHONPATH="/app/Host/src"
ENV CLASHBOT_HOST_IP="0.0.0.0"

# Expose the ui2client Bridge Port
EXPOSE 29170

# Launch the Host Engine using xvfb (X Virtual FrameBuffer)
# This allows PySide6 to run headlessly in the cloud container without crashing
CMD ["xvfb-run", "-a", "--server-args=-screen 0 1024x768x24", "python", "/app/Host/run.py"]
