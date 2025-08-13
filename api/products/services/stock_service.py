import logging
from django.db import transaction
from django.core.exceptions import ValidationError
from typing import Union, Dict, Any
from products.models import Product, Size

logger = logging.getLogger("stock_service")


class StockService:
    """
    A static service class for handling stock operations including reservation
    and unreservation of products and their size variants. All operations are
    atomic to ensure data integrity in concurrent environments.
    """
    @staticmethod
    @transaction.atomic
    def reserve_stock(product_id, quantity, size=None) -> Union[Product, Size]:
        """
        Reserve stock for a given product or its size variant.

        Args:
            product_id (int): ID of the product to reserve.
            quantity (int): Quantity of stock to reserve.
            size (str, optional): Size variant to reserve if the product has sizes.

        Returns:
            Union[Product, Size]: The updated Product or Size instance.

        Raises:
            ValidationError: If the size is required but not provided, or
                             if insufficient stock is available.
        """
        product = Product.objects.select_for_update().get(pk=product_id)

        if product.has_sizes:
            if not size:
                logger.error("Size must be specified for products with sizes.")
                raise ValidationError(
                    "Size must be specified for products with sizes.")
            size_obj = Size.objects.select_for_update().get(product=product, size=size)
            if size_obj.available_quantity < quantity:
                logger.error(
                    "Not enough stock available for size %s of product %s.", size, product_id)
                raise ValidationError(
                    "Not enough stock available for this size.")
            size_obj.available_quantity -= quantity
            size_obj.reserved_quantity += quantity
            size_obj.save()
            return size_obj

        if product.available_quantity < quantity:
            logger.error(
                "Not enough stock available for product %s.", product_id)
            raise ValidationError("Not enough stock available.")
        product.available_quantity -= quantity
        product.reserved_quantity += quantity
        product.save()
        return product

    @staticmethod
    @transaction.atomic
    def unreserve_stock(product_id, quantity, size=None, returned=True) -> Union[Product, Size]:
        """
        Unreserve stock for a given product or its size variant.

        Args:
            product_id (int): ID of the product to unreserve.
            quantity (int): Quantity of stock to unreserve.
            size (str, optional): Size variant to unreserve if applicable.
            returned (bool): Whether the stock is being returned to available stock
            (should be false when sale is completed).

        Returns:
            Union[Product, Size]: The updated Product or Size instance.

        Notes:
            If the reserved quantity goes below zero, it will be reset to zero
            and a warning will be logged.

        Raises:
            ValidationError: If the size is required but not provided.
        """
        product = Product.objects.select_for_update().get(pk=product_id)

        if product.has_sizes:
            if not size:
                logger.error("Size must be specified for products with sizes.")
                raise ValidationError(
                    "Size must be specified for products with sizes.")
            size_obj = Size.objects.select_for_update().get(product=product, size=size)
            if returned:
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
        if returned:
            product.available_quantity += quantity
        product.reserved_quantity -= quantity
        if product.reserved_quantity < 0:
            logger.warning(
                "Reserved quantity for product %s went negative (adjusting to 0).", product_id
            )
            product.reserved_quantity = 0
        product.save()
        return product
