# Dockerfile for production build of the API service
# This Dockerfile sets up the environment for running the Django application with Supervisor for process management.
# It installs necessary dependencies, copies the application code, and configures Supervisor to manage the application
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /api

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    python3-dev \
    default-libmysqlclient-dev \
    pkg-config \
    libjpeg-dev \
    zlib1g-dev \
    build-essential \
    supervisor \
    vim \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ /api/requirements/
RUN pip install --upgrade pip
RUN pip install -r requirements/prod.txt

COPY . .

COPY builds/prod/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
