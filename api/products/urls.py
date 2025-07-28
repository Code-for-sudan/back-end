from .views import ProductViewSet
from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'', ProductViewSet, basename='product')

urlpatterns = []

urlpatterns += router.urls
