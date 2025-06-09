from . import views
from django.urls import path


urlpatterns = [
    path('login/', views.login, name='login'),
    path('google/auth', views.google_login, name='google_auth'),
    path('google/callback', views.google_callback, name='google_callback'),
    path('verify_otp', views.verify_otp, name='verify_otp'),
    path('resend_otp', views.resend_otp, name='resend_otp'),
    path('reset_password_confirm/', views.reset_password_confirm, name="reset_password_confirm")
]
