#!/bin/bash
set -a
source .env  # or .env.prod or .env, as needed
source .env.prod  # Load production environment variables if needed
set +a
celery -A api worker --loglevel=info
