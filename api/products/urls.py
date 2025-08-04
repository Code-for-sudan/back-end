from .views.views import (
    DeleteProductOfferView,
    DeleteProductSizeView,
    ProductViewSet)
from .views.favourites_view import (
    FavouriteProductsView,
    AddToFavouritesView,
    RemoveFromFavouritesView)
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
    path("favourites/",
         FavouriteProductsView.as_view(),
         name="favourites"),
    path("<int:product_id>/set-favourite/",
         AddToFavouritesView.as_view(),
         name="set-favourite"),
    path("<int:product_id>/unset-favourite/",
         RemoveFromFavouritesView.as_view(),
         name="unset-favourite"),
]

urlpatterns += router.urls
