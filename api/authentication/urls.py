from . import views
from django.urls import path


urlpatterns = [
    path('google/auth', views.google_login, name='google_auth'),
    path('google/callback', views.google_callback, name='google_callback'),
    path('otp/verify', views.verify_otp, name='verify_otp'),
]