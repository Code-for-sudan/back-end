from django.test import TestCase
from django.utils import timezone
from stores.models import Store


class StoreModelTests(TestCase):
    """
    Test suite for the Store model.
    Covers:
    - Creation of Store with required and optional fields.
    - __str__ method returns the store's name.
    - created_at is set automatically.
    """

    def test_create_store_with_required_fields(self):
        store = Store.objects.create(name="My Store")
        self.assertEqual(store.name, "My Store")
        self.assertEqual(store.description, "")
        self.assertIsNotNone(store.created_at)

    def test_create_store_with_description(self):
        store = Store.objects.create(name="Desc Store", description="A test store description.")
        self.assertEqual(store.description, "A test store description.")

    def test_str_method_returns_name(self):
        store = Store.objects.create(name="String Store")
        self.assertEqual(str(store), "String Store")

    def test_created_at_auto_now_add(self):
        store = Store.objects.create(name="Time Store")
        self.assertIsNotNone(store.created_at)
        # created_at should be very close to now
        now = timezone.now()
        delta = now - store.created_at
        self.assertTrue(abs(delta.total_seconds()) < 5)

