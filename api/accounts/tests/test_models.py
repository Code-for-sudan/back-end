import hashlib
from django.test import TestCase
from django.utils import timezone
from ..models import User



class UserModelOTPTests(TestCase):
    """
    Test suite for OTP (One-Time Password) functionality in the User model.
    This class covers the following scenarios:
    - Generating an OTP sets the correct OTP value and expiry time.
    - Generating a new OTP overwrites any previous OTP.
    - Verifying an OTP succeeds with the correct code and clears OTP fields.
    - Verifying an OTP fails with an incorrect code and does not clear OTP fields.
    - Verifying an OTP fails if the OTP has expired and does not clear OTP fields.
    - Verifying an OTP fails if no OTP is set.
    - The string representation of the User model includes email, first name, last name, and gender.
    """

    def setUp(self):
        self.user = User.objects.create(
            email="otpuser@example.com",
            first_name="OTP",
            last_name="User"
        )

    def test_generate_otp_sets_otp_and_expiry(self):
        otp_code = self.user.generate_otp()
        self.assertTrue(otp_code.isdigit())
        self.assertEqual(len(otp_code), 6)
        expected_hashed = hashlib.sha256(otp_code.encode()).hexdigest()
        self.user.refresh_from_db()
        self.assertEqual(self.user.otp, expected_hashed)
        self.assertIsNotNone(self.user.otp_expires_at)
        now = timezone.now()
        delta = self.user.otp_expires_at - now
        self.assertTrue(0 < delta.total_seconds() <= 5 * 60 + 5)

    def test_generate_otp_overwrites_previous_otp(self):
        otp1 = self.user.generate_otp()
        otp2 = self.user.generate_otp()
        self.user.refresh_from_db()
        self.assertNotEqual(otp1, otp2)
        self.assertEqual(self.user.otp, hashlib.sha256(otp2.encode()).hexdigest())

    def test_verify_otp_success_and_clears_fields(self):
        otp_code = self.user.generate_otp()
        self.assertTrue(self.user.verify_otp(otp_code))
        self.user.refresh_from_db()
        self.assertIsNone(self.user.otp)
        self.assertIsNone(self.user.otp_expires_at)

    def test_verify_otp_fails_with_wrong_code(self):
        self.user.generate_otp()
        self.assertFalse(self.user.verify_otp("000000"))
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.otp)

    def test_verify_otp_fails_when_expired(self):
        otp_code = self.user.generate_otp()
        # Manually expire OTP
        self.user.otp_expires_at = timezone.now() - timezone.timedelta(minutes=1)
        self.user.save()
        self.assertFalse(self.user.verify_otp(otp_code))
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.otp)

    def test_verify_otp_fails_when_no_otp_set(self):
        self.assertFalse(self.user.verify_otp("123456"))

    def test_str_method(self):
        s = str(self.user)
        self.assertIn(self.user.email, s)
        self.assertIn(self.user.first_name, s)
        self.assertIn(self.user.last_name, s)
        self.assertIn(self.user.gender, s)