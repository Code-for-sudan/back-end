import logging
from django.conf import settings
from django.db import models
from stores.models import Store
from django.core.exceptions import ValidationError
from django.utils.timezone import now


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return str(self.name)


class Tag(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return str(self.name)


class ProductQuerySet(models.QuerySet):
    def delete(self):
        return super().update(is_deleted=True)

    def hard_delete(self):
        return super().delete()

    def alive(self):
        return self.filter(is_deleted=False)

    def dead(self):
        return self.filter(is_deleted=True)


class Product(models.Model):
    logger = logging.getLogger(__name__)
    """
    Represents a product entity with key details such as
    name, description, price, category, image, color, size, quantity,
    and associations to its owner and store.

    Attributes:
        product_name (CharField): The name of the product (max length 255).
        product_description (TextField): A detailed textual description of the product.
        price (DecimalField): The price of the product (maximum 10 digits, 2 decimal places).
        picture (ImageField): Image of the product, uploaded to the 'products/' directory.
        color (CharField): Optional color of the product (max length 50).
        size (CharField): Optional size of the product (max length 50).
        available_quantity (PositiveIntegerField): The quantity of the product available in stock (0 or more).
        reserved_quantity (BigIntegerField): The quantity currently reserved (optional).
        has_sizes (BooleanField): Indicates if the product has size variants.
        properties (JSONField): Optional custom properties (key-value structure) defined by the seller.
        owner (ForeignKey): Reference to the User who owns the product.
        store (ForeignKey): Reference to the Store where the product is listed.
        created_at (DateTimeField): Timestamp marking when the product was created (auto-set on creation).
        tags (ManyToManyField): Tags associated with the product via the ProductTag join table.

    Methods:
        __str__(): Returns the product's name as its string representation.

    Properties:
        store_name (str): Returns the name of the associated store.
        store_location (str): Returns the location of the associated store.
    """

    product_name = models.CharField(max_length=255)
    product_description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    color = models.CharField(max_length=50, blank=True, null=True)
    brand = models.CharField(max_length=100, blank=True, null=True)
    available_quantity = models.IntegerField(blank=True, null=True)
    reserved_quantity = models.BigIntegerField(blank=True, null=True)
    has_sizes: models.BooleanField = models.BooleanField(default=False)
    owner_id = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="products"
    )
    store = models.ForeignKey(
        Store, on_delete=models.CASCADE, related_name="products")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    category = models.CharField(max_length=100)
    properties = models.JSONField(blank=True, null=True)
    tags = models.ManyToManyField(
        Tag, related_name="products", through="ProductTag")
    picture = models.ImageField(upload_to="products/")
    is_deleted = models.BooleanField(default=False)

    objects = ProductQuerySet.as_manager()

    def delete(self, using=None, keep_parents=False, hard=False):
        if hard:
            return super().delete(using=using, keep_parents=keep_parents)
        self.is_deleted = True
        self.sizes.all().update(is_deleted=True, deleted_at=now())
        self.save(update_fields=["is_deleted"])

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    def __str__(self):
        return f"{self.product_name} - {self.store.name}" if self.store else self.product_name

    @property
    def current_price(self):
        """
        Returns the offer price if there is an active offer,
        otherwise returns the regular product price.
        """
        offer = getattr(self, "offer", None)  # Safe access
        if offer and offer.is_active:
            return offer.offer_price
        return self.price

    @property
    def store_name(self):
        return self.store.name

    @property
    def store_location(self):
        return self.store.location

    def clean(self):
        if self.has_sizes:
            if self.reserved_quantity is not None:
                self.logger.error(
                    "reserved_quantity must be null when has_sizes is True.")
                raise ValidationError(
                    {"reserved_quantity": "must be null when has_sizes is True."}
                )
            if self.available_quantity is not None:
                self.logger.error(
                    "available_quantity must be null when has_sizes is True.")
                raise ValidationError(
                    {"available_quantity": "must be null when has_sizes is True."}
                )
        else:
            if self.reserved_quantity is None:
                self.logger.error(
                    "reserved_quantity cannot be null when has_sizes is False.")
                raise ValidationError(
                    {"reserved_quantity": "Cannot be null when has_sizes is False."}
                )
            if self.available_quantity is None:
                self.logger.error(
                    "available_quantity cannot be null when has_sizes is False.")
                raise ValidationError(
                    {"available_quantity": "Cannot be null when has_sizes is False."}
                )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def reserve_stock(self, quantity):
        """Reserve stock for this product"""
        if quantity <= 0:
            raise ValidationError("Quantity must be positive.")
            
        if self.has_sizes:
            raise ValidationError("Cannot reserve stock on product with sizes. Use Size.reserve_stock() instead.")
        
        if self.available_quantity < quantity:
            raise ValidationError(f"Insufficient stock. Available: {self.available_quantity}, Requested: {quantity}")
        
        self.available_quantity -= quantity
        self.reserved_quantity += quantity
        self.save(update_fields=['available_quantity', 'reserved_quantity'])

    def unreserve_stock(self, quantity):
        """Unreserve stock for this product"""
        if quantity <= 0:
            raise ValidationError("Quantity must be positive.")
            
        if self.has_sizes:
            raise ValidationError("Cannot unreserve stock on product with sizes. Use Size.unreserve_stock() instead.")
        
        if self.reserved_quantity < quantity:
            raise ValidationError(f"Cannot unreserve more than reserved. Reserved: {self.reserved_quantity}, Requested: {quantity}")
        
        self.reserved_quantity -= quantity
        self.available_quantity += quantity
        self.save(update_fields=['available_quantity', 'reserved_quantity'])

    def confirm_stock_sale(self, quantity):
        """Confirm stock sale (remove from reserved quantity)"""
        if quantity <= 0:
            raise ValidationError("Quantity must be positive.")
            
        if self.has_sizes:
            raise ValidationError("Cannot confirm stock sale on product with sizes. Use Size.confirm_stock_sale() instead.")
        
        if self.reserved_quantity < quantity:
            raise ValidationError(f"Cannot confirm more than reserved. Reserved: {self.reserved_quantity}, Requested: {quantity}")
        
        self.reserved_quantity -= quantity
        self.save(update_fields=['reserved_quantity'])

    def confirm_sale(self, quantity):
        """Confirm sale (alias for confirm_stock_sale for compatibility)"""
        return self.confirm_stock_sale(quantity)

    def has_stock(self, quantity):
        """Check if product has enough available stock"""
        if self.has_sizes:
            return sum(size.available_quantity for size in self.sizes.all()) >= quantity
        return self.available_quantity >= quantity

    def get_total_stock(self):
        """Get total stock (available + reserved)"""
        if self.has_sizes:
            return sum(size.available_quantity + size.reserved_quantity for size in self.sizes.all())
        return self.available_quantity + self.reserved_quantity

    def get_available_stock(self):
        """Get available stock"""
        if self.has_sizes:
            return sum(size.available_quantity for size in self.sizes.all())
        return self.available_quantity

    def get_reserved_stock(self):
        """Get reserved stock"""
        if self.has_sizes:
            return sum(size.reserved_quantity for size in self.sizes.all())
        return self.reserved_quantity

    def confirm_size_sale(self, size_name, quantity):
        """Confirm sale for a specific size (remove from reserved quantity)"""
        if not self.has_sizes:
            raise ValidationError("Cannot confirm size sale on product without sizes.")
        
        try:
            size_obj = self.sizes.get(size=size_name)
            size_obj.confirm_stock_sale(quantity)
        except Size.DoesNotExist:
            raise ValidationError(f"Size '{size_name}' not found for this product.")

    def reserve_size_stock(self, size_name, quantity):
        """Reserve stock for a specific size"""
        if not self.has_sizes:
            raise ValidationError("Cannot reserve size stock on product without sizes.")
        
        try:
            size_obj = self.sizes.get(size=size_name)
            size_obj.reserve_stock(quantity)
        except Size.DoesNotExist:
            raise ValidationError(f"Size '{size_name}' not found for this product.")

    def unreserve_size_stock(self, size_name, quantity):
        """Unreserve stock for a specific size"""
        if not self.has_sizes:
            raise ValidationError("Cannot unreserve size stock on product without sizes.")
        
        try:
            size_obj = self.sizes.get(size=size_name)
            size_obj.unreserve_stock(quantity)
        except Size.DoesNotExist:
            raise ValidationError(f"Size '{size_name}' not found for this product.")


class ProductHistory(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, related_name="history", null=True)
    product_name = models.CharField(max_length=255)
    product_description = models.TextField()
    product_price = models.DecimalField(max_digits=10, decimal_places=2)  # Changed from 'price'
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    color = models.CharField(max_length=50, blank=True, null=True)
    brand = models.CharField(max_length=100, blank=True, null=True)
    has_sizes: models.BooleanField = models.BooleanField(default=False)
    sizes = models.JSONField(blank=True, null=True)
    owner_full_name = models.CharField(max_length=255, blank=True, null=True)
    owner_email = models.EmailField(blank=True, null=True)
    owner_phone = models.CharField(max_length=20, blank=True, null=True)
    category = models.CharField(max_length=100)
    properties = models.JSONField(blank=True, null=True)
    picture = models.ImageField(upload_to="history/products/")
    is_deleted = models.BooleanField(default=False)
    store_name = models.CharField(max_length=255, blank=True, null=True)
    store_location = models.CharField(max_length=255, blank=True, null=True)
    snapshot_taken_at = models.DateTimeField(auto_now_add=True)  # Changed from 'recorded_at'

    @classmethod
    def create_from_product(cls, product: Product):
        """
        Create and save a ProductHistory record from a Product instance.
        """
        owner = product.owner_id
        store = product.store
        sizes = []
        if product.has_sizes:
            sizes = list(product.sizes.values_list("size", flat=True))
        history = cls.objects.create(
            product=product,
            product_name=product.product_name,
            product_description=product.product_description,
            product_price=product.price,  # Updated field name
            current_price=product.current_price,
            color=product.color,
            brand=product.brand,
            has_sizes=product.has_sizes,
            sizes=sizes,
            owner_full_name=getattr(owner, "get_full_name", lambda: None)(),
            owner_email=getattr(owner, "email", None),
            owner_phone=getattr(owner, "phone_number", None),
            category=product.category,
            properties=product.properties,
            picture=product.picture,
            is_deleted=product.is_deleted,
            store_name=store.name if store else None,
            store_location=store.location if store else None,
        )
        return history

    def has_product_changed(self, product: Product) -> bool:
        # Compare key fields - updated field name
        fields_to_check = [
            ("product_name", "product_name"),
            ("product_description", "product_description"), 
            ("product_price", "price"),  # Map history field to product field
            ("current_price", "current_price"),
            ("color", "color"),
            ("brand", "brand"),
            ("has_sizes", "has_sizes"),
            ("category", "category"),
            ("properties", "properties"),
            ("picture", "picture"),
            ("is_deleted", "is_deleted")
        ]

        for history_field, product_field in fields_to_check:
            if getattr(self, history_field) != getattr(product, product_field):
                return True
     
        # Compare store fields
        store = product.store
        if self.store_name != (store.name if store else None):
            return True
        if self.store_location != (store.location if store else None):
            return True
   
        # Compare owner-related fields
        owner = product.owner_id
        owner_full_name = getattr(owner, "get_full_name", lambda: None)()
        if self.owner_full_name != owner_full_name:
            return True

        owner_email = getattr(owner, "email", None)
        if self.owner_email != owner_email:
            return True

        owner_phone = getattr(owner, "phone_number", None)
        if self.owner_phone != owner_phone:
            return True

        # Compare sizes (only names)
        product_sizes = list(product.sizes.values_list("size", flat=True))
        history_sizes = getattr(self, "sizes", []) or []
        if sorted(product_sizes) != sorted(history_sizes):
            return True

        return False

    def __str__(self):
        """String representation of ProductHistory"""
        return f"History for {self.product_name} at {self.snapshot_taken_at}"

    @property
    def price(self):
        """Backward compatibility property for tests"""
        return self.product_price


class Offer(models.Model):
    """
    Represents a product offer with a discounted price for a limited time.
    """
    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, related_name="offer")
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    offer_price = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_active(self):
        """Return True if the current date is within the offer period."""
        current_time = now()
        print(
            f"DEBUG: start_date={self.start_date} ({type(self.start_date)}), end_date={self.end_date} ({type(self.end_date)})")
        return self.start_date <= current_time <= self.end_date


class SizeManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class Size(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="sizes")
    size = models.CharField(max_length=50)
    available_quantity = models.IntegerField()
    reserved_quantity = models.BigIntegerField()
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    objects = SizeManager()
    all_objects = models.Manager()

    def delete(self, using=None, keep_parents=False):
        """Soft delete the size."""
        self.is_deleted = True
        self.deleted_at = now()
        self.save()

    def restore(self):
        """Restore a soft-deleted size."""
        self.is_deleted = False
        self.deleted_at = None
        self.save()

    def reserve_stock(self, quantity):
        """Reserve stock for this size"""
        if self.available_quantity < quantity:
            raise ValidationError(f"Insufficient stock for size {self.size}. Available: {self.available_quantity}, Requested: {quantity}")
        
        self.available_quantity -= quantity
        self.reserved_quantity += quantity
        self.save(update_fields=['available_quantity', 'reserved_quantity'])

    def unreserve_stock(self, quantity):
        """Unreserve stock for this size"""
        if self.reserved_quantity < quantity:
            raise ValidationError(f"Cannot unreserve more than reserved for size {self.size}. Reserved: {self.reserved_quantity}, Requested: {quantity}")
        
        self.reserved_quantity -= quantity
        self.available_quantity += quantity
        self.save(update_fields=['available_quantity', 'reserved_quantity'])

    def confirm_stock_sale(self, quantity):
        """Confirm stock sale (remove from reserved quantity)"""
        if self.reserved_quantity < quantity:
            raise ValidationError(f"Cannot confirm more than reserved for size {self.size}. Reserved: {self.reserved_quantity}, Requested: {quantity}")
        
        self.reserved_quantity -= quantity
        self.save(update_fields=['reserved_quantity'])

    def has_stock(self, quantity):
        """Check if size has enough available stock"""
        return self.available_quantity >= quantity

    def get_total_stock(self):
        """Get total stock (available + reserved) for this size"""
        return self.available_quantity + self.reserved_quantity

    def __str__(self):
        return f"{self.product.product_name} - {self.size}"  # type: ignore

# this model is unused should be removed in the future
class ProductTag(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("product", "tag")
