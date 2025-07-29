import logging
from django.db import transaction
from django.core.exceptions import ValidationError
from typing import Union, Dict, Any
from products.models import Product, Size

logger = logging.getLogger("stock_service")

class StockService:

    @staticmethod
    @transaction.atomic
    def reserve_stock(product_id, quantity, size=None) -> Union[Product, Size]:
        """Reserve stock for a product, optionally with size specification"""
        try:
            product = Product.objects.select_for_update().get(pk=product_id)

            if product.has_sizes:
                if not size:
                    logger.error("Size must be specified for products with sizes.")
                    raise ValidationError("Size must be specified for products with sizes.")
                
                try:
                    size_obj = Size.objects.select_for_update().get(product=product, size=size)
                except Size.DoesNotExist:
                    logger.error("Size %s not found for product %s.", size, product_id)
                    raise ValidationError(f"Size '{size}' not available for this product.")
                
                if size_obj.available_quantity < quantity:
                    logger.error("Not enough stock available for size %s of product %s.", size, product_id)
                    raise ValidationError("Not enough stock available for this size.")
                
                size_obj.available_quantity -= quantity
                size_obj.reserved_quantity += quantity
                size_obj.save()
                logger.info("Reserved %d units of size %s for product %s", quantity, size, product_id)
                return size_obj

            # For products without sizes
            if product.available_quantity < quantity:
                logger.error("Not enough stock available for product %s.", product_id)
                raise ValidationError("Not enough stock available.")
            
            product.available_quantity -= quantity
            product.reserved_quantity += quantity
            product.save()
            logger.info("Reserved %d units for product %s", quantity, product_id)
            return product

        except Product.DoesNotExist:
            logger.error("Product %s not found.", product_id)
            raise ValidationError("Product not found.")

    @staticmethod
    @transaction.atomic
    def unreserve_stock(product_id, quantity, size=None) -> Union[Product, Size]:
        """Unreserve stock for a product, optionally with size specification"""
        try:
            product = Product.objects.select_for_update().get(pk=product_id)

            if product.has_sizes:
                if not size:
                    logger.error("Size must be specified for products with sizes.")
                    raise ValidationError("Size must be specified for products with sizes.")
                
                try:
                    size_obj = Size.objects.select_for_update().get(product=product, size=size)
                except Size.DoesNotExist:
                    logger.error("Size %s not found for product %s.", size, product_id)
                    raise ValidationError(f"Size '{size}' not available for this product.")
                
                size_obj.available_quantity += quantity
                size_obj.reserved_quantity -= quantity
                
                # Ensure reserved quantity doesn't go negative
                if size_obj.reserved_quantity < 0:
                    logger.warning(
                        "Reserved quantity for size %s of product %s went negative (adjusting to 0).",
                        size, product_id
                    )
                    size_obj.reserved_quantity = 0
                
                size_obj.save()
                logger.info("Unreserved %d units of size %s for product %s", quantity, size, product_id)
                return size_obj

            # For products without sizes
            product.available_quantity += quantity
            product.reserved_quantity -= quantity
            
            # Ensure reserved quantity doesn't go negative
            if product.reserved_quantity < 0:
                logger.warning(
                    "Reserved quantity for product %s went negative (adjusting to 0).", product_id
                )
                product.reserved_quantity = 0
            
            product.save()
            logger.info("Unreserved %d units for product %s", quantity, product_id)
            return product

        except Product.DoesNotExist:
            logger.error("Product %s not found.", product_id)
            raise ValidationError("Product not found.")

    @staticmethod
    @transaction.atomic
    def confirm_stock_sale(product_id, quantity, size=None) -> Union[Product, Size]:
        """Convert reserved stock to sold stock (deduct from reserved quantity)"""
        try:
            product = Product.objects.select_for_update().get(pk=product_id)

            if product.has_sizes:
                if not size:
                    logger.error("Size must be specified for products with sizes.")
                    raise ValidationError("Size must be specified for products with sizes.")
                
                try:
                    size_obj = Size.objects.select_for_update().get(product=product, size=size)
                except Size.DoesNotExist:
                    logger.error("Size %s not found for product %s.", size, product_id)
                    raise ValidationError(f"Size '{size}' not available for this product.")
                
                if size_obj.reserved_quantity < quantity:
                    logger.error("Not enough reserved stock for size %s of product %s.", size, product_id)
                    raise ValidationError("Not enough reserved stock for this size.")
                
                size_obj.reserved_quantity -= quantity
                size_obj.sold_quantity = getattr(size_obj, 'sold_quantity', 0) + quantity
                size_obj.save()
                logger.info("Confirmed sale of %d units of size %s for product %s", quantity, size, product_id)
                return size_obj

            # For products without sizes
            if product.reserved_quantity < quantity:
                logger.error("Not enough reserved stock for product %s.", product_id)
                raise ValidationError("Not enough reserved stock.")
            
            product.reserved_quantity -= quantity
            product.sold_quantity = getattr(product, 'sold_quantity', 0) + quantity
            product.save()
            logger.info("Confirmed sale of %d units for product %s", quantity, product_id)
            return product

        except Product.DoesNotExist:
            logger.error("Product %s not found.", product_id)
            raise ValidationError("Product not found.")

    @staticmethod
    def check_stock_availability(product_id, quantity, size=None) -> Dict[str, Any]:
        """Check if stock is available without reserving it"""
        try:
            product = Product.objects.get(pk=product_id)
            
            if product.has_sizes:
                if not size:
                    return {
                        'available': False,
                        'error': 'Size must be specified for products with sizes.',
                        'available_quantity': 0
                    }
                
                try:
                    size_obj = Size.objects.get(product=product, size=size)
                    available = size_obj.available_quantity >= quantity
                    return {
                        'available': available,
                        'available_quantity': size_obj.available_quantity,
                        'reserved_quantity': size_obj.reserved_quantity,
                        'total_quantity': size_obj.available_quantity + size_obj.reserved_quantity
                    }
                except Size.DoesNotExist:
                    return {
                        'available': False,
                        'error': f"Size '{size}' not available for this product.",
                        'available_quantity': 0
                    }
            
            # For products without sizes
            available = product.available_quantity >= quantity
            return {
                'available': available,
                'available_quantity': product.available_quantity,
                'reserved_quantity': product.reserved_quantity,
                'total_quantity': product.available_quantity + product.reserved_quantity
            }

        except Product.DoesNotExist:
            return {
                'available': False,
                'error': 'Product not found.',
                'available_quantity': 0
            }

    @staticmethod
    def get_stock_info(product_id, size=None) -> Dict[str, Any]:
        """Get detailed stock information for a product"""
        try:
            product = Product.objects.get(pk=product_id)
            
            if product.has_sizes:
                if size:
                    try:
                        size_obj = Size.objects.get(product=product, size=size)
                        return {
                            'product_id': product_id,
                            'size': size,
                            'available_quantity': size_obj.available_quantity,
                            'reserved_quantity': size_obj.reserved_quantity,
                            'sold_quantity': getattr(size_obj, 'sold_quantity', 0),
                            'total_quantity': size_obj.available_quantity + size_obj.reserved_quantity
                        }
                    except Size.DoesNotExist:
                        return {'error': f"Size '{size}' not found for this product."}
                else:
                    # Return all sizes for the product
                    sizes = Size.objects.filter(product=product)
                    return {
                        'product_id': product_id,
                        'has_sizes': True,
                        'sizes': [
                            {
                                'size': s.size,
                                'available_quantity': s.available_quantity,
                                'reserved_quantity': s.reserved_quantity,
                                'sold_quantity': getattr(s, 'sold_quantity', 0)
                            } for s in sizes
                        ]
                    }
            
            # For products without sizes
            return {
                'product_id': product_id,
                'has_sizes': False,
                'available_quantity': product.available_quantity,
                'reserved_quantity': product.reserved_quantity,
                'sold_quantity': getattr(product, 'sold_quantity', 0),
                'total_quantity': product.available_quantity + product.reserved_quantity
            }

        except Product.DoesNotExist:
            return {'error': 'Product not found.'}

    @staticmethod
    def bulk_check_availability(items) -> Dict[str, Any]:
        """Check availability for multiple items at once"""
        results = {}
        total_available = True
        
        for item in items:
            product_id = item.get('product_id')
            quantity = item.get('quantity', 1)
            size = item.get('size')
            
            check_result = StockService.check_stock_availability(product_id, quantity, size)
            results[product_id] = check_result
            
            if not check_result.get('available', False):
                total_available = False
        
        return {
            'all_available': total_available,
            'items': results
        }
