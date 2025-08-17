import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import BusinessOwner
from notifications.tasks import send_email_task
from .tasks import send_activation_email_task
from django.conf import settings

# Create a signal loogger
logger = logging.getLogger("signals")
# Get the user model
User = get_user_model()

@receiver(post_save, sender=User)
def user_created_handler(sender, instance, created, **kwargs):
    """
    Signal handler for user creation events.
    This function is triggered when a new user instance is created. If the user is not a business owner,
    it sends a generic welcome email asynchronously. Regardless of user type, it schedules an activation
    email to be sent after a 60-second delay.
    Args:
        sender: The model class that sent the signal.
        instance: The instance of the user that was created.
        created (bool): Indicates whether a new record was created.
        **kwargs: Additional keyword arguments passed by the signal.
    Side Effects:
        - Sends a welcome email to non-business owner users.
        - Schedules an activation email for all users.
    """
    if created:
        # Only send generic email if not a business owner
        if not hasattr(instance, 'business_owner_profile'):
            send_email_task.delay(
                subject="Welcome to Our Platform!",
                template_name="welocmig_user",
                context={
                    "first_name": instance.first_name,   
                },
                recipient_list=[instance.email],
                email_host_user=settings.EMAIL_HOST_USER_NO_REPLY,
                email_host_password=settings.EMAIL_HOST_PASSWORD_NO_REPLY,
                from_email=settings.EMAIL_HOST_USER_NO_REPLY
            )
        # After sending the welcome email:
        send_activation_email_task.apply_async(
            args=[instance.id],
            countdown=60
        )  # 60 seconds delay


@receiver(post_save, sender=BusinessOwner)
def business_owner_created_handler(sender, instance, created, **kwargs):
    """
    Signal handler for the creation of a BusinessOwner instance.
    When a new BusinessOwner is created, this handler sends a welcome email to the associated user
    and schedules an activation email to be sent after a 60-second delay.
    Args:
        sender: The model class that sent the signal.
        instance: The instance of BusinessOwner that was created.
        created (bool): Whether the instance was created (True) or updated (False).
        **kwargs: Additional keyword arguments passed by the signal.
    """
    if created:
        send_email_task.delay(
            subject="Welcome, Business Partner!",
            template_name="welcome-business-owner",
            context={
               "first_name": instance.user.first_name,
            },
            recipient_list=[instance.user.email],
            email_host_user=settings.EMAIL_HOST_USER_NO_REPLY,
            email_host_password=settings.EMAIL_HOST_PASSWORD_NO_REPLY,
            from_email=settings.EMAIL_HOST_USER_NO_REPLY
        )
        # After sending the welcome email:
        send_activation_email_task.apply_async(
            args=[instance.id],
            countdown=60
        )  # 60 seconds delay
