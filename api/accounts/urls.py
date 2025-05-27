from . import views
from django.urls import path


urlpatterns = [
    path('auth/reset-password/verify/', views.verfy_otp, name='verfy_otp'),
]