from . import views
from django.urls import path

urlpatterns = [
    path('login/', views.login, name='login'),
    path('reset-password/confirm/', views.reset_password_confirm, name='reset-password-confirm'),
]
