#!/usr/bin/env python3
"""Django's command-line utility for administrative tasks."""
import os
import sys
from dotenv import load_dotenv

# Check if the base environment file exists
# This file is used to load common environment variables
# across different environments.
# It should be created manually or provided by the user.
try:
    load_dotenv('.env')
except FileNotFoundError:
    print("Base environment file '.env.base' not found.")
    sys.exit(1)

# Determine environment from the environment variable
# This variable should be set in the environment where the script is run.
# It can be 'dev', 'staging', or 'prod'.
# The default value is 'dev' if not set.
DJANGO_ENV = os.getenv('DJANGO_ENV', 'dev')  # Default to 'dev'
# Map to env file
try:
    env_file = '.env.{}'.format(DJANGO_ENV)
    if not os.path.exists(env_file):
        raise FileNotFoundError(f"Environment file '{env_file}' not found.")
except FileNotFoundError as e:
    print(
        "Environment file not found, error: {}."
        " Please create the file or set the environment variable.".format(e)
    )
    sys.exit(1)

# Load the appropriate .env file
load_dotenv(env_file, override=True)


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
