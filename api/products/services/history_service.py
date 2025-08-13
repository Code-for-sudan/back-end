from products.models import ProductHistory


def create_product_history_if_changed(product):
    """Check if the latest history differs from the product and create a new record if needed."""
    last_history = product.history.order_by('-snapshot_taken_at').first()
    if not last_history or last_history.has_product_changed(product):
        return ProductHistory.create_from_product(product)
    return None


def get_product_history_as_of(product, date):
    """
    Get the latest history snapshot of the product as of a given date.
    Returns None if no history exists before or on that date.
    """
    return product.history.filter(snapshot_taken_at__lte=date).order_by('-snapshot_taken_at').first()
