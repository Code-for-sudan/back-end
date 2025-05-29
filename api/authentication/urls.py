from . import views
from django.urls import path


urlpatterns = [
    path('google/auth', views.login_view, name='google_auth'),
    path('google/callback', views.callback_view, name='google_callback'),
]