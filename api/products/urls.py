from .views import DeleteProductSizeView, ProductViewSet
from django.urls import path
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'', ProductViewSet, basename='product',)

urlpatterns = [path('<int:product_id>/sizes/<int:size_id>/delete/',
                    DeleteProductSizeView.as_view(),
                    name='delete-product-size'),]

urlpatterns += router.urls
