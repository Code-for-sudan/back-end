from . import views
from django.urls import path


urlpatterns = [
    path('signup_user/', views.sign_up_user, name='signup_user'),
]
