from django.test import TestCase
from unittest.mock import patch, MagicMock
from rest_framework.exceptions import ValidationError
from ..serializers import LoginSerializer



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

    @patch('authentication.serializers.authenticate')
    def test_validate_success(self, mock_authenticate):
        mock_user = MagicMock()
        mock_authenticate.return_value = mock_user

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
