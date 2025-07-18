#!/bin/bash
set -a
export $(cat .env | grep -v '^#' | xargs)
export $(cat .env.prod | grep -v '^#' | xargs)
set +a
celery -A api worker --loglevel=info
