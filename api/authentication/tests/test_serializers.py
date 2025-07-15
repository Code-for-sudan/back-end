from django.test import TestCase
from unittest.mock import patch, MagicMock
from accounts.models import User, BusinessOwner
from stores.models import Store
from rest_framework.exceptions import ValidationError
from ..serializers import (
    GoogleAuthCodeSerializer,
    SetAccountTypeSerializer,
    SellerSetupSerializer,
    LoginSerializer,
    ResendVerificationSerializer
)



class TestLoginSerializer(TestCase):
    """
    Test suite for the LoginSerializer used in the authentication module.
    This class contains unit tests to verify the behavior of the LoginSerializer, ensuring that:
    - A user can successfully authenticate with valid credentials.
    - An appropriate validation error is raised when invalid credentials are provided.
    - Required fields ('email' and 'password') are enforced during validation.
    Test Methods:
        - test_validate_success: Verifies that valid credentials result in successful validation and user retrieval.
        - test_validate_invalid_credentials: Ensures that invalid credentials raise a ValidationError with the correct message.
        - test_validate_missing_fields: Checks that missing required fields result in validation errors for both 'email' and 'password'.
    """

    @patch('authentication.serializers.User.objects.get')
    @patch('authentication.serializers.authenticate')
    def test_validate_success(self, mock_authenticate, mock_get):
        mock_user = MagicMock()
        mock_user.is_active = True
        mock_authenticate.return_value = mock_user
        mock_get.return_value = mock_user

        data = {'email': 'test@example.com', 'password': 'secret'}
        serializer = LoginSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['user'], mock_user)

    @patch('authentication.serializers.authenticate')
    def test_validate_invalid_credentials(self, mock_authenticate):
        mock_authenticate.return_value = None
        data = {'email': 'wrong@example.com', 'password': 'wrongpass'}
        serializer = LoginSerializer(data=data)
        with self.assertRaises(ValidationError) as context:
            serializer.is_valid(raise_exception=True)
        self.assertIn("Invalid email or password.", str(context.exception))

    def test_validate_missing_fields(self):
        serializer = LoginSerializer(data={})
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
        self.assertIn('password', serializer.errors)



class GoogleAuthCodeSerializerTests(TestCase):
    def test_valid_data(self):
        data = {"code": "abc123", "state": "accountType=seller"}
        serializer = GoogleAuthCodeSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["code"], "abc123")
        self.assertEqual(serializer.validated_data["state"], "accountType=seller")

    def test_missing_code(self):
        data = {"state": "accountType=seller"}
        serializer = GoogleAuthCodeSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("code", serializer.errors)

    def test_blank_state(self):
        data = {"code": "abc123", "state": ""}
        serializer = GoogleAuthCodeSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["state"], "")

class SetAccountTypeSerializerTests(TestCase):
    def test_valid_seller(self):
        data = {"account_type": "seller"}
        serializer = SetAccountTypeSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["account_type"], "seller")

    def test_valid_buyer(self):
        data = {"account_type": "buyer"}
        serializer = SetAccountTypeSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["account_type"], "buyer")

    def test_invalid_type(self):
        data = {"account_type": "admin"}
        serializer = SetAccountTypeSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("account_type", serializer.errors)

    def test_missing_type(self):
        data = {}
        serializer = SetAccountTypeSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("account_type", serializer.errors)


class SellerSetupSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="seller@example.com", password="pass", is_store_owner=True)
        self.store = Store.objects.create(name="Old Store", location="Old Location", store_type="Retail", description="Old Desc")
        self.owner = BusinessOwner.objects.create(user=self.user, store=self.store)

    def test_valid_data(self):
        data = {
            "store_name": "New Store",
            "store_location": "New Location",
            "store_type": "Online",
            "store_description": "New Desc"
        }
        serializer = SellerSetupSerializer(data=data, context={"user": self.user})
        self.assertTrue(serializer.is_valid())
        store = serializer.save()
        self.store.refresh_from_db()
        self.assertEqual(store.name, "New Store")
        self.assertEqual(store.location, "New Location")
        self.assertEqual(store.store_type, "Online")
        self.assertEqual(store.description, "New Desc")

    def test_missing_fields(self):
        data = {
            "store_name": "",
            "store_location": "",
            "store_type": "",
            "store_description": ""
        }
        serializer = SellerSetupSerializer(data=data, context={"user": self.user})
        self.assertFalse(serializer.is_valid())
        self.assertIn("store_name", serializer.errors)

    def test_no_business_owner(self):
        user2 = User.objects.create_user(email="buyer@example.com", password="pass", is_store_owner=False)
        data = {
            "store_name": "Should Fail",
            "store_location": "Nowhere",
            "store_type": "None",
            "store_description": "No business owner"
        }
        serializer = SellerSetupSerializer(data=data, context={"user": user2})
        self.assertTrue(serializer.is_valid())
        with self.assertRaisesMessage(Exception, "Business owner profile not found for this user."):
            serializer.save()


class ResendVerificationSerializerTests(TestCase):
    def test_valid_email(self):
        data = {"email": "user@example.com"}
        serializer = ResendVerificationSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["email"], "user@example.com")

    def test_missing_email(self):
        serializer = ResendVerificationSerializer(data={})
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_invalid_email(self):
        data = {"email": "not-an-email"}
        serializer = ResendVerificationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)