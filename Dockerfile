# Pull base image
FROM python:3.12.2-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create and set work directory called `app`
RUN mkdir -p /code
WORKDIR /code

# Install dependencies
COPY requirements.txt /tmp/requirements.txt

# Install system dependencies
RUN apt update && apt install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    ffmpeg \
    libsndfile1 \
    portaudio19-dev \
    python3-pyaudio \
    && rm -rf /var/lib/apt/lists/*

RUN set -ex && \
    pip install --upgrade pip && \
    pip install -r /tmp/requirements.txt && \
    rm -rf /root/.cache/

# Create media directories and set permissions
RUN mkdir -p /code/media/lesson_images /code/media/lesson_audio && \
    chmod -R 755 /code/media

# Copy local project
COPY . /code/