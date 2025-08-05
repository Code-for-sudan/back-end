import logging
from django.conf import settings
from django.db import models
from accounts.models import User
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
        price (DecimalField): The original price of the product (maximum 10 digits, 2 decimal places).
        picture (ImageField): Image of the product, uploaded to the 'products/' directory.
        color (CharField): Optional color of the product (max length 50).
        available_quantity (int): Quantity currently available for purchase.
        Only applicable when `has_sizes` is False.
        reserved_quantity (int): Quantity reserved (e.g., items in carts awaiting payments)
        and thus not available for sale. Only applicable when `has_sizes` is False.
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
        current_price (DecimalField): The effective price of the product
        (i.e. offer price if an active offer exists else original price).
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
    classification = models.CharField(max_length=100, null=True)
    properties = models.JSONField(blank=True, null=True)
    tags = models.ManyToManyField(
        Tag, related_name="products", through="ProductTag")
    picture = models.ImageField(upload_to="products/")
    is_deleted = models.BooleanField(default=False)
    favourited_by = models.ManyToManyField(
        User,
        blank=True,
        related_name='favourite_products')
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


class ProductHistory(models.Model):
    """
    Stores historical snapshots of a product whenever it is updated.

    This model is useful for tracking changes to important product details over time.
    Each record represents the state of a product at a specific point.
    """
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, related_name="history", null=True)
    product_name = models.CharField(max_length=255)
    product_description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    color = models.CharField(max_length=50, blank=True, null=True)
    brand = models.CharField(max_length=100, blank=True, null=True)
    has_sizes: models.BooleanField = models.BooleanField(default=False)
    sizes = models.JSONField(blank=True, null=True)
    owner_full_name = models.CharField(max_length=255, blank=True, null=True)
    owner_email = models.EmailField(blank=True, null=True)
    owner_phone = models.CharField(max_length=20, blank=True, null=True)
    category = models.CharField(max_length=100)
    classification = models.CharField(max_length=100, null=True)
    properties = models.JSONField(blank=True, null=True)
    picture = models.ImageField(upload_to="history/products/")
    is_deleted = models.BooleanField(default=False)
    store_name = models.CharField(max_length=255, blank=True, null=True)
    store_location = models.CharField(max_length=255, blank=True, null=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

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
            price=product.price,
            current_price=product.current_price,
            color=product.color,
            brand=product.brand,
            has_sizes=product.has_sizes,
            sizes=sizes,
            owner_full_name=getattr(owner, "get_full_name", lambda: None)(),
            owner_email=getattr(owner, "email", None),
            owner_phone=getattr(owner, "phone_number", None),
            category=product.category,
            classification=product.classification,
            properties=product.properties,
            picture=product.picture,
            is_deleted=product.is_deleted,
            store_name=store.name if store else None,
            store_location=store.location if store else None,
        )
        return history

    def has_product_changed(self) -> bool:
        """
        Checks if product has changed since this history instance was taken.
        """
        # Compare key fields
        fields_to_check = [
            "product_name", "product_description", "price", "current_price",
            "color", "brand", "has_sizes", "category", "properties",
            "picture", "is_deleted", "store_name", "store_location"
        ]

        for field in fields_to_check:

            if getattr(self.product, field) != getattr(self, field):
                return True
        # Compare owner-related fields
        owner = self.product.owner_id

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
        product_sizes = list(self.product.sizes.values_list("size", flat=True))
        history_sizes = getattr(self, "sizes", []) or []
        if sorted(product_sizes) != sorted(history_sizes):
            return True

        return False


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
        return self.start_date <= current_time <= self.end_date


class SizeManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class Size(models.Model):
    """
    Represents a specific size variant of a product.

    Attributes:
        size (str): The size label (e.g., 'S', 'M', 'L').
        available_quantity (int): Quantity currently available for purchase.
        reserved_quantity (int): Quantity reserved (e.g., items in carts awaiting payments)
            and thus not available for sale.
    """
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

    def __str__(self):
        return f"{self.product.product_name} - {self.size}"  # type: ignore


class ProductTag(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("product", "tag")
