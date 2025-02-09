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


RUN apt update && apt install -y build-essential libssl-dev libffi-dev

RUN set -ex && \
    pip install --upgrade pip && \
    pip install -r /tmp/requirements.txt && \
    rm -rf /root/.cache/

# Copy local project
COPY . /code/