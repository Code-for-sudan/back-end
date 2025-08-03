from accounts.models import BusinessOwner, User
from products.models import Offer, Product, Size
from stores.models import Store
from typing import Literal
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from datetime import timedelta


class TestHelpers:
    @staticmethod
    def get_valid_products_data():
        """
        Helper to get a list of valid product data dictionaries with descriptions.

        Returns:
            list[dict]: Each item contains a 'description' and 'data' key.
        """
        products_with_description = []

        # Base products
        products_with_description.append({
            "description": "Product without sizes, no offer",
            "data": TestHelpers.get_valid_product_data_without_sizes()
        })

        products_with_description.append({
            "description": "Product with sizes, no offer",
            "data": TestHelpers.get_valid_product_data_with_size()
        })

        # Products with offers (active, expired, future)
        offer_labels = ["active", "expired", "future"]
        offer_dates_list = [
            TestHelpers.get_active_offer_dates(),
            TestHelpers.get_expired_offer_dates(),
            TestHelpers.get_future_offer_dates(),
        ]

        for label, offer_dates in zip(offer_labels, offer_dates_list):
            product_with_size = TestHelpers.get_valid_product_data_with_size()
            product_without_size = TestHelpers.get_valid_product_data_without_sizes()

            product_with_size = TestHelpers.add_offer_to_product_data(
                product_with_size, *offer_dates, offer_price='15.99')
            product_without_size = TestHelpers.add_offer_to_product_data(
                product_without_size, *offer_dates, offer_price='15.99')

            products_with_description.append({
                "description": f"Product with sizes and {label} offer",
                "data": product_with_size
            })

            products_with_description.append({
                "description": f"Product without sizes and {label} offer",
                "data": product_without_size
            })

        return products_with_description

    @staticmethod
    def get_active_offer_dates():
        """
        Helper to get a tuple of start and end dates for an active offer.
        Returns:
            tuple: (start_date, end_date)
        """
        start_date = timezone.now() - timedelta(days=1)
        end_date = start_date + timedelta(days=30)
        return str(start_date), str(end_date)

    @staticmethod
    def get_expired_offer_dates():
        """
        Helper to get a tuple of start and end dates for an expired offer.
        Returns:
            tuple: (start_date, end_date)
        """
        start_date = (timezone.now() - timedelta(days=60))
        end_date = (start_date + timedelta(days=30))
        return str(start_date), str(end_date)

    @staticmethod
    def get_future_offer_dates():
        """
        Helper to get a tuplse of start and end dates for a future offer.
        Returns:
            tuple: (start_date, end_date)
        """
        start_date = (timezone.now() + timedelta(days=1))
        end_date = (start_date + timedelta(days=30))
        return str(start_date), str(end_date)

    @staticmethod
    def get_valid_product_data_without_sizes(
            product_name='Test Product',
            product_description='A great product.',
            price='19.99',
            category='Electronics',
            color='Red',
            available_quantity=10):
        return {
            'product_name': product_name,
            'product_description': product_description,
            'price': price,
            'category': category,
            'picture': TestHelpers.create_test_image(),
            'color': color,
            'has_sizes': False,
            'available_quantity': available_quantity,
        }

    @staticmethod
    def get_valid_product_data_with_size(
        product_name='Test Product',
        product_description='A great product.',
        price='19.99',
        category='Electronics',
        color='Red',
        sizes=None
    ):
        if sizes is None:
            sizes = [{"size": "M", "available_quantity": 5},
                     {"size": "L", "available_quantity": 3}]
        return {
            'product_name': product_name,
            'product_description': product_description,
            'price': price,
            'category': category,
            'picture': TestHelpers.create_test_image(),
            'color': color,
            'has_sizes': True,
            'sizes': sizes,
        }

    @staticmethod
    def add_offer_to_product_data(
            product_data,
            start_date,
            end_date,
            offer_price):
        """
        Helper to add an offer to a product.
        """
        product_data = product_data.copy()
        product_data['offer'] = {
            "start_date": start_date,
            "end_date": end_date,
            "offer_price": offer_price
        }
        return product_data

    @staticmethod
    def creat_product(product_data, owner, store):
        """
        Helper to create a product instance along with optional sizes and offer.

        Args:
            product_data (dict): Dictionary containing product fields.
            owner (User): The user who owns the product.
            store (Store): The store to which the product belongs.

        Returns:
            Product: The created product instance.
        """

        # Extract and temporarily remove nested fields
        sizes = product_data.pop("sizes", None)
        offer_data = product_data.pop("offer", None)

        # Inject required foreign keys
        product_data["owner_id"] = owner
        product_data["store"] = store

        # Create the base product
        product = Product.objects.create(**product_data)

        # Create sizes if provided
        if product.has_sizes and sizes:
            for size in sizes:
                Size.objects.create(
                    product=product,
                    size=size["size"],
                    available_quantity=size.get("available_quantity", 0),
                    reserved_quantity=0,
                )

        # Create offer if provided
        if offer_data:
            Offer.objects.create(
                product=product,
                start_date=offer_data["start_date"],
                end_date=offer_data["end_date"],
                offer_price=offer_data["offer_price"],
            )

        return product

    @staticmethod
    def create_test_image():
        """Helper to create a new SimpleUploadedFile for image field."""
        return SimpleUploadedFile(
            name='test_image.jpg',
            content=b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xFF\xFF\xFF\x21\xF9\x04\x01\x0A\x00\x01\x00\x2C\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x4C\x01\x00\x3B',
            content_type='image/jpeg'
        )

    @staticmethod
    def create_user(
            email='owner@example.com',
            password='testpass123',
            first_name='Owner',
            last_name='User',
            account_type: Literal['seller', 'buyer'] = 'seller') -> User:
        return User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            account_type=account_type,
            is_active=True
        )

    @staticmethod
    def create_store(name='Test Store', location='Test Location'):
        return Store.objects.create(name=name, location=location)

    @staticmethod
    def create_business_owner(user, store):
        return BusinessOwner.objects.create(user=user, store=store)

    @staticmethod
    def create_seller(email='owner@example.com',
                      password='testpass123',
                      first_name='Owner',
                      last_name='User',
                      account_type: Literal['seller', 'buyer'] = 'seller',
                      store_name='Test Store',
                      location='Test Location'):
        user = TestHelpers.create_user(email=email,
                                       password=password,
                                       first_name=first_name,
                                       last_name=last_name,
                                       account_type=account_type)
        store = TestHelpers.create_store(name=store_name, location=location)
        business_owner = TestHelpers.create_business_owner(
            user=user, store=store)
        return user, store, business_owner
