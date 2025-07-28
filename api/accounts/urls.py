from . import views, favourites_view
from django.urls import path


urlpatterns = [
    path('signup/user/', views.SignupUserView.as_view(), name='signup_user'),
    path('signup/business/', views.SignupBusinessOwnerView.as_view(),
         name='signup_business_owner'),
    path('favourites/', favourites_view.FavouriteProductsView.as_view(),
         name='list-favourites'),
    path('favourites/add/<int:product_id>/',
         favourites_view.AddToFavouritesView.as_view(),
         name='add-to-favourites'),
    path('favourites/remove/<int:product_id>/',
         favourites_view.RemoveFromFavouritesView.as_view(),
         name='remove-from-favourites'),

]
