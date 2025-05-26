"""
Celery configuration file for Django API project.
"""
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery


# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')

# Create celery app instance
app = Celery('sudamall_backend')

# Load celery config from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Set the autodiscover to True
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    """
    A Celery task for debugging purposes.

    This task prints the details of the current request to the console.
    It is primarily used for testing and debugging Celery task execution.

    Args:
        self: The task instance that is bound to this method.

    Example:
        When this task is called, it will output the request details:
        >>> debug_task.apply_async()
        Request: <Context details of the task>
    """
    print(f'Request: {self.request!r}')
    
# Import periodic tasks for Celery Beat
from celery.schedules import crontab
from celery import shared_task
