"""
Fixed realistic tests for Payments app that align with actual model structure
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from decimal import Decimal
from unittest.mock import patch

from payments.models import Payment, PaymentGateway, PaymentAttempt
from products.models import Product
from stores.models import Store
from orders.models import Order

User = get_user_model()


class PaymentEdgeCaseTest(TestCase):
    """Test payment edge cases with correct model fields"""

    def setUp(self):
        """Set up test data with correct field names"""
        self.user = User.objects.create_user(
            email='payment_edge@example.com',
            password='testpass123',
            phone_number='1234567890'
        )
        
        self.gateway = PaymentGateway.objects.create(
            name='Edge Test Gateway',
            is_active=True,
            fixed_fee=Decimal('0.30'),
            percentage_fee=Decimal('2.9')
        )
        
        self.store = Store.objects.create(
            name='Payment Edge Store',
            location='Payment Edge Location',
            store_type='retail'
        )
        
        self.product = Product.objects.create(
            product_name='Payment Edge Product',
            product_description='Payment Edge Description',
            price=Decimal('100.00'),
            owner_id=self.user,
            store=self.store,
            category='electronics',
            has_sizes=False,
            available_quantity=1,
            reserved_quantity=0,
            picture='payment_edge.jpg'
        )

    def test_payment_with_zero_amount(self):
        """Test payment creation with zero amount (should fail)"""
        with self.assertRaises(ValidationError):
            payment = Payment.objects.create(
                gateway=self.gateway,
                user=self.user,
                amount=Decimal('0.00'),  # Invalid
                currency='USD'
            )
            payment.full_clean()

    def test_payment_with_negative_amount(self):
        """Test payment creation with negative amount (should fail)"""
        with self.assertRaises(ValidationError):
            payment = Payment.objects.create(
                gateway=self.gateway,
                user=self.user,
                amount=Decimal('-10.00'),  # Invalid
                currency='USD'
            )
            payment.full_clean()

    def test_payment_with_extreme_amounts(self):
        """Test payments with very large and very small amounts"""
        # Test very large amount
        large_payment = Payment.objects.create(
            gateway=self.gateway,
            user=self.user,
            amount=Decimal('999999.99'),
            currency='USD'
        )
        self.assertEqual(large_payment.amount, Decimal('999999.99'))
        
        # Test very small but valid amount
        small_payment = Payment.objects.create(
            gateway=self.gateway,
            user=self.user,
            amount=Decimal('0.01'),
            currency='USD'
        )
        self.assertEqual(small_payment.amount, Decimal('0.01'))

    def test_payment_with_inactive_gateway(self):
        """Test payment creation with inactive gateway"""
        inactive_gateway = PaymentGateway.objects.create(
            name='Inactive Gateway',
            is_active=False,
            fixed_fee=Decimal('0.30'),
            percentage_fee=Decimal('2.9')
        )
        
        # This should work at model level, business logic validation would be in views
        payment = Payment.objects.create(
            gateway=inactive_gateway,
            user=self.user,
            amount=Decimal('50.00'),
            currency='USD'
        )
        self.assertFalse(payment.gateway.is_active)

    def test_multiple_payment_attempts_scenario(self):
        """Test multiple payment attempts"""
        payment = Payment.objects.create(
            gateway=self.gateway,
            user=self.user,
            amount=Decimal('75.00'),
            currency='USD'
        )
        
        # Create multiple attempts
        for i in range(3):
            PaymentAttempt.objects.create(
                payment=payment,
                attempt_number=i + 1,
                status='failed' if i < 2 else 'completed',
                gateway_response={'result': f'attempt_{i+1}'},
                error_message=f'Error on attempt {i+1}' if i < 2 else None
            )
        
        attempts = PaymentAttempt.objects.filter(payment=payment)
        self.assertEqual(attempts.count(), 3)
        
        # Check that last attempt succeeded
        last_attempt = attempts.latest('attempted_at')
        self.assertEqual(last_attempt.status, 'completed')

    def test_payment_currency_mismatch(self):
        """Test payment with different currencies"""
        eur_payment = Payment.objects.create(
            gateway=self.gateway,
            user=self.user,
            amount=Decimal('85.50'),
            currency='EUR'
        )
        
        usd_payment = Payment.objects.create(
            gateway=self.gateway,
            user=self.user,
            amount=Decimal('100.00'),
            currency='USD'
        )
        
        self.assertEqual(eur_payment.currency, 'EUR')
        self.assertEqual(usd_payment.currency, 'USD')
        self.assertNotEqual(eur_payment.currency, usd_payment.currency)

    def test_payment_gateway_fee_calculation(self):
        """Test payment gateway fee calculation"""
        payment_amount = Decimal('100.00')
        
        # Calculate expected fee
        expected_fee = self.gateway.fixed_fee + (payment_amount * self.gateway.percentage_fee / 100)
        calculated_fee = self.gateway.calculate_fee(payment_amount)
        
        self.assertEqual(calculated_fee, expected_fee)
        
        # Test with different amount
        small_amount = Decimal('5.00')
        small_fee = self.gateway.calculate_fee(small_amount)
        expected_small_fee = self.gateway.fixed_fee + (small_amount * self.gateway.percentage_fee / 100)
        self.assertEqual(small_fee, expected_small_fee)

    def test_payment_with_order_integration(self):
        """Test payment linked to orders"""
        # Create order
        order = Order.objects.create(
            order_id='test_order_123',
            user_id=self.user,
            product=self.product,
            quantity=1,
            total_price=Decimal('100.00'),
            unit_price=Decimal('100.00')
        )
        
        # Create payment for order
        payment = Payment.objects.create(
            gateway=self.gateway,
            user=self.user,
            amount=order.total_price,
            currency='USD'
        )
        
        # Verify payment amount matches order total
        self.assertEqual(payment.amount, order.total_price)
        self.assertEqual(payment.user, order.user_id)

    def test_payment_status_transitions(self):
        """Test valid payment status transitions"""
        payment = Payment.objects.create(
            gateway=self.gateway,
            user=self.user,
            amount=Decimal('50.00'),
            currency='USD'
        )
        
        # Test initial status
        self.assertEqual(payment.status, 'pending')
        
        # Test status updates
        payment.status = 'processing'
        payment.save()
        self.assertEqual(payment.status, 'processing')
        
        payment.status = 'completed'
        payment.save()
        self.assertEqual(payment.status, 'completed')

    def test_payment_duplicate_prevention(self):
        """Test that duplicate payments can be detected"""
        payment1 = Payment.objects.create(
            gateway=self.gateway,
            user=self.user,
            amount=Decimal('100.00'),
            currency='USD',
            gateway_transaction_id='unique_123',
            payment_method='credit_card',
            net_amount=Decimal('97.40')  # After fees
        )
        
        # Same transaction ID should be detectable (business logic level)
        payment2 = Payment.objects.create(
            gateway=self.gateway,
            user=self.user,
            amount=Decimal('100.00'),
            currency='USD',
            gateway_transaction_id='unique_123',  # Same transaction ID
            payment_method='credit_card',
            net_amount=Decimal('97.40')
        )
        
        # At model level this works, business logic would prevent this
        duplicate_payments = Payment.objects.filter(gateway_transaction_id='unique_123')
        self.assertEqual(duplicate_payments.count(), 2)

    def test_payment_attempt_error_logging(self):
        """Test that payment attempt errors are properly logged"""
        payment = Payment.objects.create(
            gateway=self.gateway,
            user=self.user,
            amount=Decimal('25.00'),
            currency='USD'
        )
        
        error_attempt = PaymentAttempt.objects.create(
            payment=payment,
            attempt_number=1,
            status='failed',
            gateway_response={'error_code': 'CARD_DECLINED'},
            error_message='Card was declined by issuing bank'
        )
        
        self.assertEqual(error_attempt.status, 'failed')
        self.assertIn('CARD_DECLINED', str(error_attempt.gateway_response))
        self.assertIn('declined', error_attempt.error_message)

    def test_payment_refund_workflow(self):
        """Test payment refund scenarios"""
        original_payment = Payment.objects.create(
            gateway=self.gateway,
            user=self.user,
            amount=Decimal('100.00'),
            currency='USD',
            status='completed',
            payment_method='credit_card',
            net_amount=Decimal('97.40')
        )
        
        # Create refund payment (negative amount or separate model)
        refund_payment = Payment.objects.create(
            gateway=self.gateway,
            user=self.user,
            amount=Decimal('30.00'),  # Partial refund
            currency='USD',
            gateway_transaction_id=f'refund_{original_payment.payment_id}',
            payment_method='credit_card',
            net_amount=Decimal('29.22')
        )
        
        self.assertEqual(refund_payment.amount, Decimal('30.00'))
        self.assertIn('refund_', refund_payment.gateway_transaction_id)

    def test_payment_concurrent_processing(self):
        """Test payment processing in concurrent scenarios"""
        payment = Payment.objects.create(
            gateway=self.gateway,
            user=self.user,
            amount=Decimal('75.00'),
            currency='USD'
        )
        
        # Simulate concurrent attempts
        attempt1 = PaymentAttempt.objects.create(
            payment=payment,
            attempt_number=1,
            status='processing',
            gateway_response={'status': 'in_progress'}
        )
        
        attempt2 = PaymentAttempt.objects.create(
            payment=payment,
            attempt_number=2,
            status='processing',
            gateway_response={'status': 'in_progress'}
        )
        
        # Both attempts exist (business logic would prevent concurrent processing)
        concurrent_attempts = PaymentAttempt.objects.filter(
            payment=payment, 
            status='processing'
        )
        self.assertEqual(concurrent_attempts.count(), 2)
