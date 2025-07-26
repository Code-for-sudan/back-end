from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Payment management
    path('create/', views.CreatePaymentView.as_view(), name='create_payment'),
    path('process/', views.ProcessPaymentView.as_view(), name='process_payment'),
    path('status/<str:order_reference>/', views.PaymentStatusView.as_view(), name='payment_status'),
    path('detail/<uuid:payment_id>/', views.PaymentDetailView.as_view(), name='payment_detail'),
    path('my-payments/', views.UserPaymentsView.as_view(), name='user_payments'),
    
    # Payment gateways
    path('gateways/', views.PaymentGatewaysView.as_view(), name='payment_gateways'),
    
    # Configuration
    path('config/', views.payment_config, name='payment_config'),
    
    # Refunds (admin only)
    path('refunds/create/', views.CreateRefundView.as_view(), name='create_refund'),
    
    # Testing endpoints (only available in test mode)
    path('test/', views.TestPaymentView.as_view(), name='test_payment'),
    path('test/webhook/', views.SimulateWebhookView.as_view(), name='simulate_webhook'),
]
