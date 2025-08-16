import os, logging
from django.test import TestCase, override_settings
from django.core.cache import cache
from rest_framework import status # type: ignore
from rest_framework.test import APITestCase # type: ignore
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch
from accounts.models import User, BusinessOwner
from stores.models import Store

# Get the user model
User = get_user_model()

# Create a logger for this module
logger = logging.getLogger('authentication_tests')


class GoogleLoginTests(TestCase):
    """
    Test suite for the Google Login API endpoint.
    """

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.url = reverse('google_auth')

    def test_google_login_redirects_to_google_auth(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['message'], 'Redirect to Google OAuth')

class GoogleLoginViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('google_auth')

    @override_settings(
        REST_FRAMEWORK={
            "DEFAULT_THROTTLE_CLASSES": [],
            "DEFAULT_THROTTLE_RATES": {},
        }
    )
    def test_google_login_url_no_account_type(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("google_oauth_url", response.data)
        self.assertIn("accounts.google.com", response.data["google_oauth_url"])

    def test_google_login_url_with_account_type(self):
        response = self.client.get(self.url, {"accountType": "seller"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("state=seller", response.data["google_oauth_url"])

class GoogleCallbackViewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.url = reverse('google_callback')

    @patch("authentication.views.authenticate_google_user")
    def test_callback_success(self, mock_auth):
        user = User.objects.create_user(email="testuser@example.com", password="pass")
        mock_auth.return_value = (user, ("access", "refresh"), True, "seller")
        payload = {"code": "valid_code", "state": "accountType=seller"}
        response = self.client.get(self.url, payload)  # Send as query params in GET
        self.assertEqual(response.status_code, 200)
        self.assertIn("token", response.data)
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["email"], "testuser@example.com")
        self.assertEqual(response.data["accountType"], "seller")
        self.assertTrue(response.data["needsAccountType"] is False)
        self.assertEqual(response.data["redirect"], "/dashboard/seller-setup")

    @patch("authentication.services.authenticate_google_user")
    def test_callback_failure(self, mock_auth):
        mock_auth.side_effect = Exception("fail")
        payload = {"code": "bad_code"}
        response = self.client.get(self.url, payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["message"], "Authentication failed.")

    def test_callback_missing_code(self):
        response = self.client.get(self.url, {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["message"], "Invalid or missing authorization code.")

class SetAccountTypeViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('set_account_type')
        self.user = User.objects.create_user(email="user@example.com", password="pass")
        self.client.force_authenticate(self.user)

    def test_set_account_type_success(self):
        payload = {"account_type": "seller"}
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "Account type updated")
        self.user.refresh_from_db()
        self.assertEqual(self.user.account_type, "seller")
        self.assertTrue(self.user.is_store_owner)

    def test_set_account_type_invalid(self):
        payload = {"account_type": "invalid"}
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, 400)

class SellerSetupViewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.url = reverse('seller_setup')
        self.user = User.objects.create_user(email="seller@example.com", password="pass", is_store_owner=True, account_type="seller")
        self.store = Store.objects.create(name="Old Store")
        self.owner = BusinessOwner.objects.create(user=self.user, store=self.store)
        self.client.force_authenticate(self.user)

    def test_seller_setup_success(self):
        payload = {
            "store_name": "New Store",
            "store_location": "Khartoum",
            "store_type": "Retail",
            "store_description": "Best store in town"
        }
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "Seller setup complete")
        self.store.refresh_from_db()
        self.assertEqual(self.store.name, "New Store")
        self.assertEqual(self.store.location, "Khartoum")
        self.assertEqual(self.store.store_type, "Retail")
        self.assertEqual(self.store.description, "Best store in town")

    def test_seller_setup_no_business_owner(self):
        user2 = User.objects.create_user(email="buyer@example.com", password="pass", is_store_owner=False, account_type="buyer")
        self.client.force_authenticate(user2)
        payload = {
            "store_name": "Should Fail",
            "store_location": "Nowhere",
            "store_type": "None",
            "store_description": "No business owner"
        }
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Business owner profile not found", str(response.data))

    def test_seller_setup_invalid_data(self):
        payload = {
            "store_name": "",
            "store_location": "",
            "store_type": "",
            "store_description": ""
        }
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("store_name", response.data)

class PasswordResetFlowTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email='reset@example.com',
            password='oldpassword',
            first_name='Reset',
            last_name='User'
        )
        self.otp = self.user.generate_otp()
        self.reset_request_url = reverse('reset_password_request')
        self.reset_verify_url = reverse('reset_password_verify')
        self.update_password_url = reverse('request_update_password')

    def test_password_reset_request_success(self):
        data = {"email": self.user.email}
        response = self.client.post(self.reset_request_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.data)

    def test_password_reset_request_missing_email(self):
        response = self.client.post(self.reset_request_url, {})
        self.assertEqual(response.status_code, 400)
        self.assertIn("message", response.data)

    def test_password_reset_request_nonexistent_user(self):
        data = {"email": "notfound@example.com"}
        response = self.client.post(self.reset_request_url, data)
        self.assertEqual(response.status_code, 200)  # Should not reveal user existence
        self.assertIn("message", response.data)

    def test_password_reset_verify_success(self):
        data = {"email": self.user.email, "otp": self.otp}
        response = self.client.post(self.reset_verify_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("random_token", response.data)
        self.assertIn("user", response.data)

    def test_password_reset_verify_invalid_otp(self):
        data = {"email": self.user.email, "otp": "wrongotp"}
        response = self.client.post(self.reset_verify_url, data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("message", response.data)

    def test_password_reset_verify_missing_fields(self):
        response = self.client.post(self.reset_verify_url, {})
        self.assertEqual(response.status_code, 400)
        self.assertIn("message", response.data)

    def test_password_reset_verify_nonexistent_user(self):
        data = {"email": "nouser@example.com", "otp": "123456"}
        response = self.client.post(self.reset_verify_url, data)
        self.assertEqual(response.status_code, 400)  # Should not reveal user existence
        self.assertIn("message", response.data)

    def test_update_password_success(self):
        # First, verify OTP to get the token
        verify_response = self.client.post(self.reset_verify_url, {"email": self.user.email, "otp": self.otp})
        token = verify_response.data.get("random_token")
        data = {
            "email": self.user.email,
            "new_password": "newsecurepassword123",
            "random_token": token
        }
        response = self.client.post(self.update_password_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newsecurepassword123"))

    def test_update_password_missing_fields(self):
        response = self.client.post(self.update_password_url, {})
        self.assertEqual(response.status_code, 400)
        self.assertIn("message", response.data)

    def test_update_password_nonexistent_user(self):
        data = {
            "email": "nouser@example.com",
            "new_password": "newsecurepassword123",
            "random_token": "invalidtoken"
        }
        response = self.client.post(self.update_password_url, data)
        self.assertEqual(response.status_code, 200)  # Should not reveal user existence
        self.assertIn("message", response.data)

    def test_update_password_invalid_token(self):
        data = {
            "email": self.user.email,
            "new_password": "newsecurepassword123",
            "random_token": "invalidtoken"
        }
        response = self.client.post(self.update_password_url, data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("message", response.data)


class ActivateAccountViewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.url = reverse('activate_account')
        self.user = User.objects.create_user(
            email="activate@example.com",
            password="testpass",
            is_active=False,
            first_name="Test",
            last_name="User"
        )
        self.token = str(RefreshToken.for_user(self.user).access_token)

    def test_activate_account_success(self):
        response = self.client.post(self.url, {"token": self.token})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertEqual(response.data["message"], "Account activated successfully.")
        self.assertEqual(response.data["user"]["email"], self.user.email)

    def test_activate_account_already_active(self):
        self.user.is_active = True
        self.user.save()
        response = self.client.post(self.url, {"token": self.token})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Account activated successfully.")

    def test_activate_account_missing_token(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Token is required.")

    def test_activate_account_invalid_token(self):
        response = self.client.post(self.url, {"token": "invalidtoken"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Invalid or expired token.")


class AccessTokenFromRefreshViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="refreshuser@example.com", password="testpass")
        self.url = reverse('token_refresh')
        self.refresh_token = str(RefreshToken.for_user(self.user))

    def test_access_token_from_valid_refresh_cookie(self):
        self.client.cookies["refresh_token"] = self.refresh_token
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertTrue(response.data["access"].startswith("ey"))

    def test_access_token_missing_refresh_cookie(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["message"], "Refresh token required.")

    def test_access_token_invalid_refresh_cookie(self):
        self.client.cookies["refresh"] = "invalidtoken"
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["message"], "Refresh token required.")

