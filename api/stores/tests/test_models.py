from ..models import Store
from django.test import TestCase
from django.utils import timezone

class StoreModelTests(TestCase):
    """
    Test suite for the Store model.
    Covers:
    - Creation of Store with required and optional fields.
    - __str__ method returns the store's name and location.
    - created_at is set automatically.
    - store_type is required and saved correctly.
    """

    def test_create_store_with_all_required_fields(self):
        store = Store.objects.create(
            name="My Store",
            description="A test store",
            location="Khartoum",
            store_type="Retail"
        )
        self.assertEqual(store.name, "My Store")
        self.assertEqual(store.description, "A test store")
        self.assertEqual(store.location, "Khartoum")
        self.assertEqual(store.store_type, "Retail")
        self.assertIsNotNone(store.created_at)

    def test_create_store_with_blank_description(self):
        store = Store.objects.create(
            name="Desc Store",
            description="",
            location="Omdurman",
            store_type="Online"
        )
        self.assertEqual(store.description, "")
        self.assertEqual(store.location, "Omdurman")
        self.assertEqual(store.store_type, "Online")

    def test_str_method_returns_name_and_location(self):
        store = Store.objects.create(
            name="String Store",
            location="Bahri",
            description="",
            store_type="Wholesale"
        )
        self.assertEqual(str(store), "String Store (Bahri)")

    def test_created_at_auto_now_add(self):
        store = Store.objects.create(
            name="Time Store",
            location="Khartoum",
            description="",
            store_type="Retail"
        )
        self.assertIsNotNone(store.created_at)
        now = timezone.now()
        delta = now - store.created_at
        self.assertTrue(abs(delta.total_seconds()) < 5)
