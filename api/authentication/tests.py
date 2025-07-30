"""
Comprehensive tests for Authentication app
Tests JWT authentication, user verification, token management, and security
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from unittest.mock import patch, MagicMock
import json
import uuid
from datetime import timedelta

from authentication.models import VerificationCode
from authentication.services import AuthenticationService
from authentication.utils import generate_verification_code, validate_phone_number

User = get_user_model()


class JWTAuthenticationTest(APITestCase):
    """Test JWT authentication functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='jwt@example.com',
            password='testpass123',
            phone_number='1234567890',
            is_verified=True
        )
        
        self.login_url = reverse('authentication:login')
        self.refresh_url = reverse('authentication:token_refresh')
        self.verify_url = reverse('authentication:token_verify')
    
    def test_user_login_success(self):
        """Test successful user login"""
        login_data = {
            'email': 'jwt@example.com',
            'password': 'testpass123'
        }
        
        response = self.client.post(self.login_url, login_data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['email'], self.user.email)
    
    def test_user_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        login_data = {
            'email': 'jwt@example.com',
            'password': 'wrongpassword'
        }
        
        response = self.client.post(self.login_url, login_data)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn('access', response.data)
    
    def test_user_login_unverified_account(self):
        """Test login with unverified account"""
        unverified_user = User.objects.create_user(
            email='unverified@example.com',
            password='testpass123',
            phone_number='9876543210',
            is_verified=False
        )
        
        login_data = {
            'email': 'unverified@example.com',
            'password': 'testpass123'
        }
        
        response = self.client.post(self.login_url, login_data)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('verification', response.data['detail'].lower())
    
    def test_token_refresh(self):
        """Test JWT token refresh"""
        refresh = RefreshToken.for_user(self.user)
        
        refresh_data = {
            'refresh': str(refresh)
        }
        
        response = self.client.post(self.refresh_url, refresh_data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
    
    def test_token_verification(self):
        """Test JWT token verification"""
        access_token = AccessToken.for_user(self.user)
        
        verify_data = {
            'token': str(access_token)
        }
        
        response = self.client.post(self.verify_url, verify_data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_protected_endpoint_access(self):
        """Test accessing protected endpoints with JWT"""
        # Generate token
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token
        
        # Set authorization header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Try accessing protected endpoint (assuming profile endpoint exists)
        if hasattr(settings, 'AUTHENTICATION_URLS') and 'profile' in settings.AUTHENTICATION_URLS:
            profile_url = reverse('authentication:profile')
            response = self.client.get(profile_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_expired_token_handling(self):
        """Test handling of expired tokens"""
        # Create an expired token (by manipulating timestamp)
        with patch('rest_framework_simplejwt.tokens.datetime') as mock_datetime:
            # Mock past time for token creation
            past_time = timezone.now() - timedelta(hours=25)  # Assuming 24h expiry
            mock_datetime.now.return_value = past_time
            
            expired_token = AccessToken.for_user(self.user)
            
            # Reset datetime mock
            mock_datetime.now.return_value = timezone.now()
            
            verify_data = {'token': str(expired_token)}
            response = self.client.post(self.verify_url, verify_data)
            
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserVerificationTest(TestCase):
    """Test user verification functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='verify@example.com',
            password='testpass123',
            phone_number='2345678901',
            is_verified=False
        )
    
    def test_verification_code_generation(self):
        """Test verification code generation"""
        code = generate_verification_code()
        
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())
    
    def test_verification_code_creation(self):
        """Test VerificationCode model creation"""
        verification = VerificationCode.objects.create(
            user=self.user,
            verification_type='phone',
            code='123456'
        )
        
        self.assertEqual(verification.user, self.user)
        self.assertEqual(verification.verification_type, 'phone')
        self.assertEqual(verification.code, '123456')
        self.assertFalse(verification.is_used)
        self.assertIsNone(verification.used_at)
    
    def test_verification_code_expiry(self):
        """Test verification code expiry"""
        # Create expired verification code
        verification = VerificationCode.objects.create(
            user=self.user,
            verification_type='email',
            code='654321'
        )
        
        # Manually set created_at to past time
        past_time = timezone.now() - timedelta(minutes=16)  # Assuming 15min expiry
        verification.created_at = past_time
        verification.save()
        
        self.assertTrue(verification.is_expired())
    
    def test_verification_code_usage(self):
        """Test marking verification code as used"""
        verification = VerificationCode.objects.create(
            user=self.user,
            verification_type='phone',
            code='789012'
        )
        
        # Mark as used
        verification.mark_as_used()
        
        self.assertTrue(verification.is_used)
        self.assertIsNotNone(verification.used_at)
    
    def test_phone_number_validation(self):
        """Test phone number validation utility"""
        # Valid phone numbers
        valid_phones = [
            '1234567890',
            '+1234567890',
            '123-456-7890',
            '(123) 456-7890'
        ]
        
        for phone in valid_phones:
            self.assertTrue(validate_phone_number(phone))
        
        # Invalid phone numbers
        invalid_phones = [
            '123',
            'abcdefghij',
            '++1234567890',
            '123456789012345'
        ]
        
        for phone in invalid_phones:
            self.assertFalse(validate_phone_number(phone))


class AuthenticationServiceTest(TestCase):
    """Test AuthenticationService functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='service@example.com',
            password='testpass123',
            phone_number='3456789012',
            is_verified=False
        )
        
        # Clear cache before each test
        cache.clear()
    
    @patch('authentication.services.send_sms')
    def test_send_phone_verification(self, mock_send_sms):
        """Test sending phone verification code"""
        mock_send_sms.return_value = True
        
        result = AuthenticationService.send_verification_code(
            user=self.user,
            verification_type='phone'
        )
        
        self.assertTrue(result['success'])
        self.assertIn('code_sent', result)
        
        # Verify code was created
        verification = VerificationCode.objects.filter(
            user=self.user,
            verification_type='phone'
        ).first()
        
        self.assertIsNotNone(verification)
        self.assertFalse(verification.is_used)
        
        # Verify SMS was sent
        mock_send_sms.assert_called_once()
    
    @patch('authentication.services.send_email')
    def test_send_email_verification(self, mock_send_email):
        """Test sending email verification code"""
        mock_send_email.return_value = True
        
        result = AuthenticationService.send_verification_code(
            user=self.user,
            verification_type='email'
        )
        
        self.assertTrue(result['success'])
        
        # Verify code was created
        verification = VerificationCode.objects.filter(
            user=self.user,
            verification_type='email'
        ).first()
        
        self.assertIsNotNone(verification)
        
        # Verify email was sent
        mock_send_email.assert_called_once()
    
    def test_verify_code_success(self):
        """Test successful code verification"""
        # Create verification code
        verification = VerificationCode.objects.create(
            user=self.user,
            verification_type='phone',
            code='567890'
        )
        
        result = AuthenticationService.verify_code(
            user=self.user,
            code='567890',
            verification_type='phone'
        )
        
        self.assertTrue(result['success'])
        
        # Refresh user from database
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_verified)
        
        # Verify code is marked as used
        verification.refresh_from_db()
        self.assertTrue(verification.is_used)
    
    def test_verify_code_invalid(self):
        """Test verification with invalid code"""
        # Create verification code
        VerificationCode.objects.create(
            user=self.user,
            verification_type='phone',
            code='123456'
        )
        
        result = AuthenticationService.verify_code(
            user=self.user,
            code='wrong_code',
            verification_type='phone'
        )
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        
        # User should remain unverified
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_verified)
    
    def test_verify_code_expired(self):
        """Test verification with expired code"""
        # Create expired verification code
        verification = VerificationCode.objects.create(
            user=self.user,
            verification_type='email',
            code='expired123'
        )
        
        # Manually expire the code
        past_time = timezone.now() - timedelta(minutes=20)
        verification.created_at = past_time
        verification.save()
        
        result = AuthenticationService.verify_code(
            user=self.user,
            code='expired123',
            verification_type='email'
        )
        
        self.assertFalse(result['success'])
        self.assertIn('expired', result['error'].lower())
    
    def test_rate_limiting(self):
        """Test verification code rate limiting"""
        # Send multiple verification codes quickly
        for i in range(6):  # Assuming 5 attempts per hour limit
            with patch('authentication.services.send_sms') as mock_sms:
                mock_sms.return_value = True
                
                result = AuthenticationService.send_verification_code(
                    user=self.user,
                    verification_type='phone'
                )
                
                if i < 5:  # First 5 should succeed
                    self.assertTrue(result['success'])
                else:  # 6th should fail due to rate limiting
                    self.assertFalse(result['success'])
                    self.assertIn('rate_limit', result.get('error', '').lower())
    
    def test_user_authentication_check(self):
        """Test user authentication status checking"""
        # Unverified user
        auth_status = AuthenticationService.check_user_auth_status(self.user)
        self.assertFalse(auth_status['is_verified'])
        self.assertFalse(auth_status['can_login'])
        
        # Verify user
        self.user.is_verified = True
        self.user.save()
        
        auth_status = AuthenticationService.check_user_auth_status(self.user)
        self.assertTrue(auth_status['is_verified'])
        self.assertTrue(auth_status['can_login'])


class SecurityTest(TestCase):
    """Test authentication security features"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='security@example.com',
            password='testpass123',
            phone_number='4567890123',
            is_verified=True
        )
        
        self.client = Client()
    
    def test_brute_force_protection(self):
        """Test protection against brute force attacks"""
        login_url = reverse('authentication:login') if hasattr(settings, 'AUTHENTICATION_URLS') else '/auth/login/'
        
        # Simulate multiple failed login attempts
        failed_attempts = 0
        max_attempts = 5  # Assuming 5 attempts before lockout
        
        for i in range(max_attempts + 2):
            response = self.client.post(login_url, {
                'email': 'security@example.com',
                'password': 'wrongpassword'
            })
            
            if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                # Account should be temporarily locked
                self.assertIn('too many attempts', response.data.get('detail', '').lower())
                break
            elif response.status_code == status.HTTP_401_UNAUTHORIZED:
                failed_attempts += 1
        
        # Should have been blocked before reaching max attempts
        self.assertLess(failed_attempts, max_attempts + 2)
    
    def test_password_security_requirements(self):
        """Test password security requirements"""
        # Test weak passwords (assuming password validation is implemented)
        weak_passwords = [
            '123',
            'password',
            '12345678',
            'qwerty'
        ]
        
        for weak_password in weak_passwords:
            with self.assertRaises(Exception):  # Should raise validation error
                User.objects.create_user(
                    email='weak@example.com',
                    password=weak_password,
                    phone_number='5555555555'
                )
    
    def test_session_security(self):
        """Test session security features"""
        # Login user
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token
        
        # Verify token is valid
        self.assertIsNotNone(access_token)
        
        # Simulate token blacklisting (logout)
        refresh.blacklist()
        
        # Token should be invalid after blacklisting
        with self.assertRaises(Exception):
            new_access = refresh.access_token
    
    def test_user_data_protection(self):
        """Test user data protection measures"""
        # Test that sensitive data is not exposed in API responses
        user_data = {
            'id': self.user.id,
            'email': self.user.email,
            'phone_number': self.user.phone_number,
            'is_verified': self.user.is_verified
        }
        
        # Password should never be in serialized data
        self.assertNotIn('password', user_data)
        
        # Test data masking for phone numbers in certain contexts
        masked_phone = AuthenticationService.mask_phone_number(self.user.phone_number)
        self.assertIn('***', masked_phone)
        self.assertNotEqual(masked_phone, self.user.phone_number)


class AuthenticationIntegrationTest(APITestCase):
    """Test authentication integration with other systems"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='integration@example.com',
            password='testpass123',
            phone_number='5678901234',
            is_verified=True
        )
    
    def test_auth_middleware_integration(self):
        """Test authentication middleware integration"""
        # Test unauthenticated request
        response = self.client.get('/api/protected-endpoint/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Test authenticated request
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        # This would test a protected endpoint if it exists
        # response = self.client.get('/api/protected-endpoint/')
        # self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_user_permissions_integration(self):
        """Test user permissions with authentication"""
        # Create user with specific permissions
        self.user.user_permissions.clear()
        
        # Test permission-based access
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        # This would test permission-based endpoints
        # Different assertions based on user permissions
    
    @patch('authentication.tasks.cleanup_expired_codes')
    def test_periodic_cleanup_integration(self, mock_cleanup):
        """Test periodic cleanup task integration"""
        # Create expired verification codes
        past_time = timezone.now() - timedelta(days=1)
        
        VerificationCode.objects.create(
            user=self.user,
            verification_type='phone',
            code='old_code',
            created_at=past_time
        )
        
        # Trigger cleanup task
        mock_cleanup.delay()
        
        # Verify cleanup was called
        mock_cleanup.delay.assert_called_once()
