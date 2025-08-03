from .views import DeleteProductOfferView, DeleteProductSizeView, ProductViewSet
from django.urls import path
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'', ProductViewSet, basename='product',)

urlpatterns = [
    path('<int:product_id>/sizes/<int:size_id>/delete/',
         DeleteProductSizeView.as_view(),
         name='delete-product-size'),
    path('<int:product_id>/offers/delete/',
         DeleteProductOfferView.as_view(),
         name='delete-product-offer'),
]

urlpatterns += router.urls
