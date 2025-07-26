from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # Payment timer endpoints
    path('payment-status/<str:order_id>/', views.OrderPaymentStatusView.as_view(), name='order-payment-status'),
    path('check-payment/<str:order_id>/', views.check_my_order_payment, name='check-my-order-payment'),
    
    # Admin cleanup endpoints
    path('admin/cleanup/expired/', views.ManualCleanupExpiredOrdersView.as_view(), name='manual-cleanup-expired'),
    path('admin/expired-count/', views.ExpiredOrdersCountView.as_view(), name='expired-orders-count'),
    path('admin/trigger-cleanup-task/', views.trigger_cleanup_task, name='trigger-cleanup-task'),
]
