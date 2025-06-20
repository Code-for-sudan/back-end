from django.db import models
from accounts.models import User
from stores.models import Store

class Product(models.Model):
    """
    Represents a product entity with details such as name, description, price, category, image URL, and associations to owner and store.
    Attributes:
        product_name (CharField): The name of the product (max length 255).
        product_description (TextField): Detailed description of the product.
        price (DecimalField): The price of the product (up to 10 digits, 2 decimal places).
        category (CharField): The category of the product (max length 100).
        picture (CharField): URL to the product's image (max length 255).
        color (CharField): Optional color of the product (max length 50).
        size (CharField): Optional size of the product (max length 50).
        quantity (PositiveIntegerField): The available quantity of the product (0 or greater).
        owner_id (ForeignKey): Reference to the User who owns the product.
        store (ForeignKey): Reference to the Store where the product is listed.
        created_at (DateTimeField): Timestamp when the product was created (auto-set on creation).
    Methods:
        __str__(): Returns the product's name as its string representation.
        store_name (property): Returns the name of the associated store.
        store_location (property): Returns the location of the associated store.
    """

    product_name = models.CharField(max_length=255)
    product_description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=100)
    picture = models.CharField(max_length=255)
    color = models.CharField(max_length=50, blank=True, null=True)
    size = models.CharField(max_length=50, blank=True, null=True)
    quantity = models.PositiveIntegerField()
    owner_id = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='products')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.product_name

    @property
    def store_name(self):
        return self.store.name

    @property
    def store_location(self):
        return self.store.location