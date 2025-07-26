# services/stock_service.py
import logging
from django.db import transaction
from django.core.exceptions import ValidationError
from typing import Union
from products.models import Product, Size

logger = logging.getLogger("stock_service")

class StockService:

    @staticmethod
    @transaction.atomic
    def reserve_stock(product_id, quantity, size=None) -> Union[Product, Size]:
        product = Product.objects.select_for_update().get(pk=product_id)

        if product.has_sizes:
            if not size:
                raise ValidationError("Size must be specified for products with sizes.")
            size_obj = Size.objects.select_for_update().get(product=product, size=size)
            if size_obj.available_quantity < quantity:
                raise ValidationError("Not enough stock available for this size.")
            size_obj.available_quantity -= quantity
            size_obj.reserved_quantity += quantity
            size_obj.save()
            return size_obj

        if product.available_quantity < quantity:
            raise ValidationError("Not enough stock available.")
        product.available_quantity -= quantity
        product.reserved_quantity += quantity
        product.save()
        return product

    @staticmethod
    @transaction.atomic
    def unreserve_stock(product_id, quantity, size=None):
        product = Product.objects.select_for_update().get(pk=product_id)

        if product.has_sizes:
            if not size:
                raise ValidationError("Size must be specified for products with sizes.")
            size_obj = Size.objects.select_for_update().get(product=product, size=size)
            size_obj.available_quantity += quantity
            size_obj.reserved_quantity -= quantity
            if size_obj.reserved_quantity < 0:
                logger.warning(
                    "Reserved quantity for size %s of product %s went negative (adjusting to 0).",
                    size, product_id
                )
                size_obj.reserved_quantity = 0
            size_obj.save()
            return size_obj

        product.available_quantity += quantity
        product.reserved_quantity -= quantity
        if product.reserved_quantity < 0:
            logger.warning(
                "Reserved quantity for product %s went negative (adjusting to 0).", product_id
            )
            product.reserved_quantity = 0
        product.save()
        return product
