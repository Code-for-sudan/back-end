from django.urls import path
from . import views

app_name = 'carts'

urlpatterns = [
    # Cart management endpoints
    path('', views.CartDetailView.as_view(), name='cart-detail'),
    path('count/', views.cart_count, name='cart-count'),
    path('add/', views.AddToCartView.as_view(), name='add-to-cart'),
    path('update/<int:cart_item_id>/', views.UpdateCartItemView.as_view(), name='update-cart-item'),
    path('remove/<int:cart_item_id>/', views.RemoveFromCartView.as_view(), name='remove-from-cart'),
    path('clear/', views.ClearCartView.as_view(), name='clear-cart'),
    
    # Validation endpoints
    path('validate/', views.ValidateCartView.as_view(), name='validate-cart'),
    
    # Checkout endpoints - new enhanced functionality
    path('checkout/single/', views.CheckoutSingleItemView.as_view(), name='checkout-single-item'),
    path('checkout/full/', views.CheckoutFullCartView.as_view(), name='checkout-full-cart'),
]
