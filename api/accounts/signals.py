import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import BusinessOwner
from notifications.tasks import send_email_task

# Create a signal loogger
logger = logging.getLogger("signals")
# Get the user model
User = get_user_model()

@receiver(post_save, sender=User)
def user_created_handler(sender, instance, created, **kwargs):
    """
    Signal handler that sends a welcome email to a newly created user.

    This function is intended to be connected to the post_save signal of the User model.
    When a new user instance is created, it triggers an asynchronous task to send a welcome email
    to the user's email address.

    Args:
        sender (Model): The model class that sent the signal.
        instance (User): The actual instance being saved.
        created (bool): A boolean indicating whether a new record was created.
        **kwargs: Additional keyword arguments passed by the signal.

    Returns:
        None
    """

    if created:
        send_email_task.delay(
            subject="Welcome to Our Platform!",
            template_name="welcome-user",
            context={
                "first_name": instance.first_name,   
            },
            recipient_list=[instance.email]
        )


@receiver(post_save, sender=BusinessOwner)
def business_owner_created_handler(sender, instance, created, **kwargs):
    """
    Signal handler that sends a welcome email to a newly created business owner.
    This function is intended to be connected to a model's post_save signal. When a new business owner instance is created,
    it triggers an asynchronous task to send a welcome email to the owner's associated user email address.
    Args:
        sender (type): The model class that sent the signal.
        instance (object): The actual instance being saved.
        created (bool): A boolean indicating whether a new record was created.
        **kwargs: Additional keyword arguments passed by the signal.
    Side Effects:
        Initiates an asynchronous email sending task if a new business owner is created.
    """

    if created:
        send_email_task.delay(
            subject="Welcome, Business Partner!",
            template_name="welcome-business-owner",
            context={
               "first_name": instance.user.first_name,
            },
            recipient_list=[instance.user.email]
        )
