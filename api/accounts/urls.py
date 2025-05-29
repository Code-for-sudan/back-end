from . import views
from django.urls import path


urlpatterns = [
    path('auth/reset-password/verify/', views.verify_otp, name='verify_otp'),
]