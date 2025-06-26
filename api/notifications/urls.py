# urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmailTemplateViewSet

router = DefaultRouter()
router.register(r'emails', EmailTemplateViewSet, basename='emails')

urlpatterns = [
    
]

urlpatterns += router.urls
