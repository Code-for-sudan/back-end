#!/bin/bash
set -a
export $(cat .env | grep -v '^#' | xargs)
export $(cat .env.prod | grep -v '^#' | xargs)
celery -A api worker --loglevel=infoariables if needed
set +a
celery -A api beat --loglevel=info
