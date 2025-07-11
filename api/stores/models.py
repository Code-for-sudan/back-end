from django.db import models


class Store(models.Model):
    """
    Represents a store entity with a name, optional description, and creation timestamp.
    Attributes:
        name (CharField): The name of the store (max length 255).
        description (TextField): Optional detailed description of the store.
        location (CharField): Optional location of the store (max length 255).
        created_at (DateTimeField): Timestamp when the store was created (auto-set on creation).
    Methods:
        __str__(): Returns the store's name as its string representation.
    """

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255,)
    created_at = models.DateTimeField(auto_now_add=True)
    store_type = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} ({self.location})"
