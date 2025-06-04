from . import views
from django.urls import path


urlpatterns = [
    path('signup_user/', views.sign_up_user, name='signup_user'),
    path('signup_bussiness_owner/', views.signup_bussiness_owner, name='signup_bussiness_owner'),
]
