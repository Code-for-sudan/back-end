# builds/dev/Dockerfile

# Use official Python base image
FROM python:3.12-slim

# Set working directory inside container
WORKDIR /app

# Install system dependencies (e.g., for psycopg2, Pillow, etc.)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements/ /app/requirements/

# Install Python dependencies (dev environment by default)
RUN pip install --upgrade pip
RUN pip install -r requirements/dev.txt

# Copy project source code
COPY . .

# Set default command
CMD ["DJANGO_ENV=dev","python", "manage.py", "runserver", "0.0.0.0:8000"]
