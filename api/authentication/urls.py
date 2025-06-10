from . import views
from django.urls import path


urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('google/auth', views.GoogleLoginView.as_view(), name='google_auth'),
    path('google/callback', views.GoogleCallbackView.as_view(), name='google_callback'),
    path('verify_otp', views.verify_otp, name='verify_otp'),
    path('resend_otp', views.resend_otp, name='resend_otp'),
    path('reset_password_confirm/', views.reset_password_confirm, name="reset_password_confirm")
]
