"""
Celery configuration file for Django API project.
"""
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery


# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')

# Create celery app instance
app = Celery('celery_api')

# Load celery config from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Set the autodiscover to True
app.autodiscover_tasks()

# Import periodic tasks for Celery Beat
from celery.schedules import crontab
from celery import shared_task
