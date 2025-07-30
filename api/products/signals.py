# products/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Product
from .services.history_service import create_product_history_if_changed

@receiver(post_save, sender=Product)
def product_saved_handler(sender, instance, created, **kwargs):
    """
    Called when a product is created or updated.
    """
    create_product_history_if_changed(instance)

@receiver(post_delete, sender=Product)
def product_deleted_handler(sender, instance, **kwargs):
    """
    Called when a product is deleted.
    For soft-delete, make sure the delete() method sets is_deleted = True
    before saving.
    """
    create_product_history_if_changed(instance)
