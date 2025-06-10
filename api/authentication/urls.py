from . import views
from django.urls import path


urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('google/auth/', views.GoogleLoginView.as_view(), name='google_auth'),
    path('google/callback/', views.GoogleCallbackView.as_view(), name='google_callback'),
    path('reset-password/verify/', views.ResetPasswordVerifyView.as_view(), name='reset_password_verify'),
    path('reset-password/request/', views.ResetPasswordRequestView.as_view(), name='reset_password_request'),
    path('reset-password/confirm/', views.ResetPasswordConfirmView.as_view(), name="reset_password_confirm")
]
