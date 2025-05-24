"""
WSGI config for api project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os
import sys
from dotenv import load_dotenv

# Determine environment
DJANGO_ENV = os.getenv('DJANGO_ENV', 'dev')  # Default to 'dev'
# Map to env file
try:
    env_file = '.env.{}'.format(DJANGO_ENV)
    if not os.path.exists(env_file):
        raise FileNotFoundError(f"Environment file '{env_file}' not found.")
except FileNotFoundError as e:
    print(e)
    sys.exit(1)

# Load the appropriate .env file
load_dotenv(env_file)


from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')

application = get_wsgi_application()
