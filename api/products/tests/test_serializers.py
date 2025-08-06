from decimal import Decimal
import json
from django.test import TestCase
from products.models import Offer, Tag
from products.serializers import ProductSerializer
import logging
from .test_helpers import TestHelpers

logger = logging.getLogger('products_tests')


class ProductSerializerTests(TestCase):
    """
    Test suite for the ProductSerializer.
    Tests:
        - test_serializer_with_valid_data: Checks that the serializer is valid with all required and optional fields.
        - test_serializer_missing_required_field: Ensures the serializer is invalid if a required field is missing.
        - test_serializer_optional_fields: Confirms that omitting optional fields does not cause validation to fail.
        - test_create_product: Verifies that a Product instance can be created with valid data and related objects.
    """

    def setUp(self):
        self.user, self.store, self.buisness_owner = TestHelpers.create_seller()

    def test_serializer_with_valid_data(self):
        for product_entry in TestHelpers.get_valid_products_data():
            description = product_entry["description"]
            product_data = product_entry["data"]
            serializer = ProductSerializer(data=product_data)
            logger.info(
                f"Validating serializer on {description}")
            self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_serializer_missing_required_field(self):
        data = TestHelpers.get_valid_product_data_without_sizes()
        data.pop('product_name')
        serializer = ProductSerializer(data=data)
        logger.info(
            f"Validating serializer with missing required field 'product_name': {data}")
        self.assertFalse(serializer.is_valid())
        logger.info(f"Serializer errors: {serializer.errors}")
        self.assertIn('product_name', serializer.errors)

    def test_serializer_optional_fields(self):
        data = TestHelpers.get_valid_product_data_without_sizes()
        data.pop('color')
        serializer = ProductSerializer(data=data)
        logger.info(
            f"Validating serializer with optional fields omitted: {data}")
        self.assertTrue(serializer.is_valid(), serializer.errors)
        logger.info("Serializer is valid without optional fields.")

    def test_missing_quantity(self):
        data = TestHelpers.get_valid_product_data_without_sizes()
        data.pop("available_quantity")
        serializer = ProductSerializer(data=data)
        logger.info(
            f"Validating serializer with missing sizes: {data}")
        self.assertFalse(serializer.is_valid())

    def test_missing_sizes(self):
        data = TestHelpers.get_valid_product_data_with_size()
        data.pop("sizes")
        serializer = ProductSerializer(data=data)
        logger.info(
            f"Validating serializer with available_quantity omitted and no sizes: {data}")
        self.assertFalse(serializer.is_valid())

    def test_size_missing_quantity(self):
        data = TestHelpers.get_valid_product_data_with_size(
            sizes=[{"size": "S"},
                   {"size": "M", "available_quantity": 5},
                   {"size": "L", "available_quantity": 3}])
        serializer = ProductSerializer(data=data)
        logger.info(
            f"Validating serializer with available_quantity omitted on one size: {data}")
        self.assertFalse(serializer.is_valid())
        self.assertIn('sizes', serializer.errors)
        self.assertIsInstance(serializer.errors['sizes'], list)
        self.assertGreaterEqual(len(serializer.errors['sizes']), 1)
        self.assertIn('available_quantity', serializer.errors['sizes'][0])

    def test_size_missing_size(self):
        data = TestHelpers.get_valid_product_data_with_size(
            sizes=[{"available_quantity": 5},
                   {"size": "L", "available_quantity": 3}])
        serializer = ProductSerializer(data=data)
        logger.info(
            f"Validating serializer with size omitted on one size: {data}")
        self.assertFalse(serializer.is_valid())
        self.assertIn('sizes', serializer.errors)
        self.assertIsInstance(serializer.errors['sizes'], list)
        self.assertGreaterEqual(len(serializer.errors['sizes']), 1)
        self.assertIn('size', serializer.errors['sizes'][0])

    def test_duplicate_size(self):
        data = TestHelpers.get_valid_product_data_with_size()
        data['sizes'].append({"size": "S", "available_quantity": 10})
        data['sizes'].append({"size": "S", "available_quantity": 3})
        serializer = ProductSerializer(data=data)
        logger.info(
            f"Validating serializer with diplicate size S: {data}")
        self.assertFalse(serializer.is_valid())
        self.assertIn("sizes", serializer.errors)

    def test_json_fields(self):
        data = TestHelpers.get_valid_product_data_without_sizes()
        data.pop("available_quantity")
        data['has_sizes'] = True
        data['sizes'] = json.dumps([
            {"size": "M", "available_quantity": 5},
            {"size": "L", "available_quantity": 3}])

        data['offer'] = json.dumps({
            "start_date": "2025-08-02",
            "end_date": "2025-08-06",
            "offer_price": 10
        })

        data["tags"] = json.dumps(["men", "kids"])
        serialzier = ProductSerializer(data=data)
        self.assertTrue(serialzier.is_valid(), serialzier.errors)

    def test_invalid_offer(self):
        data = TestHelpers.get_valid_product_data_with_size()
        offer_dates = TestHelpers.get_active_offer_dates()
        data = TestHelpers.add_offer_to_product_data(
            data, *offer_dates, offer_price=10)
        logger.info(f"validating offer missing start_date, {data}")
        data['offer'].pop("start_date")
        serialzier = ProductSerializer(data=data)
        self.assertFalse(serialzier.is_valid())
        self.assertIn('offer', serialzier.errors)
        self.assertIn("start_date", serialzier.errors['offer'])

    def test_create_product_without_size(self):
        data = TestHelpers.get_valid_product_data_without_sizes()
        serializer = ProductSerializer(data=data.copy())
        logger.info(f"Creating product with data: {data}")
        self.assertTrue(serializer.is_valid(), serializer.errors)
        product = serializer.save(owner_id=self.user, store=self.store)
        logger.info(f"Product created: {product}")
        self.assertEqual(product.product_name,
                         data['product_name'])
        self.assertEqual(product.owner_id, self.user)
        self.assertEqual(product.store, self.store)
        self.assertTrue(product.picture.name.startswith('products/test_image'))

    def test_create_product_with_tags(self):
        # First product with one tag
        data = TestHelpers.get_valid_product_data_without_sizes()
        data['tags'] = ['men']
        logger.info(f"Creating product with data: {data}")
        serializer = ProductSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        product = serializer.save(owner_id=self.user, store=self.store)
        logger.info(f"Product created: {product}")

        # Get tags from saved product
        tags = list(product.tags.values_list("name", flat=True))
        self.assertListEqual(tags, ["men"])

        tag_count = Tag.objects.count()

        # Second product with one existing and one new tag
        data = TestHelpers.get_valid_product_data_without_sizes()
        data['tags'] = ['men', 'shoe']
        logger.info(f"Creating second product with data: {data}")
        serializer = ProductSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        product = serializer.save(owner_id=self.user, store=self.store)
        logger.info(f"Product created: {product}")

        # Check that product has correct tags
        tags = list(product.tags.values_list("name", flat=True))
        self.assertListEqual(sorted(tags), ["men", "shoe"])

        # Only one new tag should be added
        self.assertEqual(Tag.objects.count(), tag_count + 1)

    def test_create_product_with_offer(self):
        data = TestHelpers.get_valid_product_data_without_sizes()
        data = TestHelpers.add_offer_to_product_data(
            data,
            *TestHelpers.get_active_offer_dates(),
            offer_price=50
        )
        serializer = ProductSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        product = serializer.save(owner_id=self.user, store=self.store)

        self.assertIsNotNone(product.offer)
        self.assertEqual(product.offer.offer_price, 50)

    def test_create_product_with_sizes(self):
        data = TestHelpers.get_valid_product_data_with_size()
        serializer = ProductSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        product = serializer.save(owner_id=self.user, store=self.store)

        self.assertEqual(product.sizes.count(), 2)
        sizes = list(product.sizes.values_list("size", flat=True))
        self.assertIn("M", sizes)
        self.assertIn("L", sizes)

    def test_update_product_retain_sizes_and_offer(self):
        # Create product first
        original_data = TestHelpers.get_valid_product_data_with_size()
        original_data = TestHelpers.add_offer_to_product_data(
            original_data,
            *TestHelpers.get_active_offer_dates(),
            60
        )
        serializer = ProductSerializer(data=original_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        product = serializer.save(owner_id=self.user, store=self.store)

        old_offer_id = product.offer.id
        old_size_ids = set(product.sizes.values_list('id', flat=True))

        # Update with no sizes or offer
        update_data = {
            'product_name': 'Updated Product Name'
        }
        serializer = ProductSerializer(
            instance=product, data=update_data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_product = serializer.save()

        self.assertEqual(updated_product.offer.id, old_offer_id)
        new_size_ids = set(updated_product.sizes.values_list('id', flat=True))
        self.assertSetEqual(new_size_ids, old_size_ids)

    def test_update_product_offer_replaces_old(self):
        data = TestHelpers.get_valid_product_data_without_sizes()
        data = TestHelpers.add_offer_to_product_data(
            data,
            *TestHelpers.get_expired_offer_dates(),
            60
        )
        serializer = ProductSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        product = serializer.save(owner_id=self.user, store=self.store)
        old_offer_id = product.offer.id

        update_data = {
            'offer': {
                "start_date": "2025-09-01",
                "end_date": "2025-09-10",
                "offer_price": 30
            }
        }
        serializer = ProductSerializer(
            instance=product, data=update_data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_product = serializer.save()

        self.assertNotEqual(updated_product.offer.id, old_offer_id)
        self.assertEqual(updated_product.offer.offer_price, 30)
        self.assertFalse(Offer.objects.filter(id=old_offer_id).exists())

    def test_update_product_sizes_with_retention_edit_and_add(self):
        data = TestHelpers.get_valid_product_data_with_size()
        serializer = ProductSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        product = serializer.save(owner_id=self.user, store=self.store)

        old_sizes = list(product.sizes.all())
        m_size = next(s for s in old_sizes if s.size == "M")

        update_data = {
            "sizes": [
                {"id": m_size.id, "size": "M", "available_quantity": 10},  # update
                {"size": "XL", "available_quantity": 2}  # new
                # "L" is omitted => should be retained
            ]
        }

        serializer = ProductSerializer(
            instance=product, data=update_data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_product = serializer.save()

        updated_sizes = list(updated_product.sizes.all())

        # Check all 3 exist
        self.assertEqual(len(updated_sizes), 3)
        self.assertTrue(
            any(s.size == "M" and s.available_quantity == 10 for s in updated_sizes))
        self.assertTrue(any(s.size == "L" for s in updated_sizes))
        self.assertTrue(any(s.size == "XL" for s in updated_sizes))

    def test_update_add_offer_to_product_without_existing_offer(self):
        # Step 1: Create a product without offer
        data = TestHelpers.get_valid_product_data_without_sizes()
        serializer = ProductSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        product = serializer.save(owner_id=self.user, store=self.store)

        self.assertFalse(hasattr(product, 'offer')
                         and product.offer is not None)

        start_date, end_date = TestHelpers.get_expired_offer_dates()
        updated_data = {
            "offer": {
                "start_date": start_date,
                "end_date": end_date,
                "offer_price": 9.99
            }
        }
        serializer = ProductSerializer(
            product, data=updated_data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        product = serializer.save()
        product.refresh_from_db()
        if hasattr(product, "offer") and product.offer:
            product.offer.refresh_from_db()
        # Step 3: Validate the offer now exists
        self.assertIsNotNone(product.offer)
        self.assertEqual(product.offer.offer_price, Decimal('9.99'))
