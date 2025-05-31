from . import views
from django.urls import path


urlpatterns = [
    path('signup/', views.sign_up, name='signup'),
]
