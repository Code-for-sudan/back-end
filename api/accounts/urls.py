from . import views
from django.urls import path


urlpatterns = [
    path('signup/user/', views.SignupUserView.as_view(), name='signup_user'),
    path('signup/business/', views.SignupBusinessOwnerView.as_view(), name='signup_business_owner'),
]
