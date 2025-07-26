from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Payment
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Payment)
def payment_status_changed(sender, instance, created, **kwargs):
    """
    Handle payment status changes and trigger appropriate actions
    """
    if not created:  # Only for updates, not new payments
        if instance.status == 'completed':
            # Payment completed successfully
            logger.info(f"Payment {instance.payment_id} completed successfully")
            
            # Here you can trigger additional actions like:
            # - Send confirmation email
            # - Update inventory
            # - Trigger order fulfillment
            # - Send notifications
            
        elif instance.status == 'failed':
            # Payment failed
            logger.warning(f"Payment {instance.payment_id} failed: {instance.failure_reason}")
            
            # Here you can trigger failure actions like:
            # - Send failure notification
            # - Release reserved stock
            # - Update order status
            
        elif instance.status == 'refunded':
            # Payment refunded
            logger.info(f"Payment {instance.payment_id} refunded")
            
            # Here you can trigger refund actions like:
            # - Update order status
            # - Restore inventory
            # - Send refund confirmation
