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
        category (ForeignKey): Reference to the Category to which the product belongs.
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
        self.save(update_fields=["is_deleted"])

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    def __str__(self):
        return str(self.product_name)
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
        print(f"DEBUG: start_date={self.start_date} ({type(self.start_date)}), end_date={self.end_date} ({type(self.end_date)})")
        return self.start_date <= current_time <= self.end_date


class Size(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="sizes")
    size = models.CharField(max_length=50)
    available_quantity = models.IntegerField()
    reserved_quantity = models.BigIntegerField()

    def __str__(self):
        return f"{self.product.product_name} - {self.size}"  # type: ignore


class ProductTag(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("product", "tag")
