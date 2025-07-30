# products/management/commands/seed_products.py
import random
from django.core.management.base import BaseCommand
from django.db import connection
from django.contrib.auth.hashers import make_password

# Product templates with base price and categories
PRODUCT_TEMPLATES = [
    {"name": "Smartphone", "description": "Latest 5G smartphone with OLED display",
        "base_price": 400, "category": "Electronics"},
    {"name": "Laptop", "description": "Lightweight laptop with 16GB RAM",
        "base_price": 800, "category": "Electronics"},
    {"name": "Sneakers", "description": "Comfortable running sneakers",
        "base_price": 60, "category": "Footwear"},
    {"name": "T-Shirt", "description": "Cotton unisex t-shirt",
        "base_price": 15, "category": "Clothing"},
    {"name": "Backpack", "description": "Waterproof travel backpack",
        "base_price": 40, "category": "Accessories"},
    {"name": "Smartwatch", "description": "Bluetooth smartwatch with heart-rate sensor",
        "base_price": 120, "category": "Electronics"},
]

# Brands by category
BRANDS = {
    "Electronics": ["Samsung", "Apple", "Sony", "Xiaomi", "Huawei"],
    "Footwear": ["Nike", "Adidas", "Puma", "New Balance"],
    "Clothing": ["H&M", "Zara", "Uniqlo", "Levi's"],
    "Accessories": ["Samsonite", "North Face", "Fjällräven", "Herschel"],
}

# Sizes for specific categories
SIZES = {
    "Clothing": ["S", "M", "L", "XL"],
    "Footwear": [str(size) for size in range(38, 46)],  # EU sizes 38-45
}

SELLERS = [
    {"email": "owner1@example.com", "first_name": "Alice", "last_name": "Smith"},
    {"email": "owner2@example.com", "first_name": "Bob", "last_name": "Johnson"},
]

STORES = [
    {"name": "Tech World", "location": "Downtown"},
    {"name": "Fashion Hub", "location": "Uptown"},
]


class Command(BaseCommand):
    help = "Seed the database with products, sellers, brands, and sizes (MySQL compatible)"

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=20,
                            help='Number of products to generate')

    def handle(self, *args, **options):
        count = options['count']
        self.stdout.write(self.style.NOTICE(f"Seeding {count} products..."))

        with connection.cursor() as cursor:
            business_owner_ids = []

            # 1. Create Users and Stores
            for i, seller in enumerate(SELLERS):
                cursor.execute("""
                    INSERT INTO accounts_user (email, first_name, last_name, password, is_active, account_type, is_store_owner)
                    VALUES (%s, %s, %s, %s, TRUE, 'seller', TRUE)
                    ON DUPLICATE KEY UPDATE 
                        is_active = VALUES(is_active),
                        first_name = VALUES(first_name),
                        last_name = VALUES(last_name);
                """, [
                    seller["email"],
                    seller["first_name"],
                    seller["last_name"],
                    make_password("testpass123"),
                ])
                cursor.execute("SELECT id FROM accounts_user WHERE email = %s", [
                               seller["email"]])
                user_id = cursor.fetchone()[0]

                store = STORES[i]
                cursor.execute("""
                    INSERT INTO stores_store (name, location)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE location = VALUES(location);
                """, [store["name"], store["location"]])
                cursor.execute(
                    "SELECT id FROM stores_store WHERE name = %s", [store["name"]])
                store_id = cursor.fetchone()[0]

                cursor.execute("""
                    INSERT IGNORE INTO accounts_businessowner (user_id, store_id)
                    VALUES (%s, %s);
                """, [user_id, store_id])

                business_owner_ids.append((user_id, store_id))

            # 2. Create Products
            for i in range(count):
                template = random.choice(PRODUCT_TEMPLATES)
                category = template['category']
                brand = random.choice(BRANDS[category])
                price = round(template['base_price'] *
                              random.uniform(0.9, 1.3), 2)
                quantity = random.randint(5, 100)
                has_sizes = category in SIZES

                user_id, store_id = random.choice(business_owner_ids)
                product_name = f"{brand} {template['name']} {i + 1}"

                # Insert product
                cursor.execute("""
                    INSERT INTO products_product
                    (product_name, product_description, price, category, brand, available_quantity,
                     reserved_quantity, has_sizes, owner_id_id, store_id, is_deleted)
                    VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s, FALSE);
                """, [
                    product_name,
                    template['description'],
                    price,
                    category,
                    brand,
                    quantity,
                    has_sizes,
                    user_id,
                    store_id,
                ])
                cursor.execute("SELECT LAST_INSERT_ID();")
                product_id = cursor.fetchone()[0]

                # Insert sizes if applicable
                if has_sizes:
                    for size in SIZES[category]:
                        size_quantity = random.randint(
                            1, quantity // len(SIZES[category]) + 1)
                        cursor.execute("""
                            INSERT INTO products_size (product_id, size, available_quantity, reserved_quantity)
                            VALUES (%s, %s, %s, 0);
                        """, [product_id, size, size_quantity])

        self.stdout.write(self.style.SUCCESS(
            f"Successfully seeded {count} products with sizes, brands, prices, and quantities!"))
