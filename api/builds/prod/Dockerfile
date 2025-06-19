# builds/prod/Dockerfile

# Use official Python base image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory inside container
WORKDIR /api

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    python3-dev \
    default-libmysqlclient-dev \
    pkg-config \
    libjpeg-dev \
    zlib1g-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements/ /api/requirements/
COPY .env /api/.env
COPY .env.prod /api/.env.prod
COPY wait-for-it.sh /api/wait-for-it.sh
RUN chmod +x /api/wait-for-it.sh
RUN pip install --upgrade pip
RUN pip install -r requirements/prod.txt

# Copy only necessary project files
COPY . .

# Collect static files (will be served by nginx)
RUN python manage.py collectstatic --noinput

# Set default command to use Gunicorn WSGI server
CMD ["gunicorn", "api.wsgi:application", "--bind", "0.0.0.0:8000"]
