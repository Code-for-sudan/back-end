from . import views
from django.urls import path


urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('google/auth/', views.GoogleLoginView.as_view(), name='google_auth'),
    path('google/callback/', views.GoogleCallbackView.as_view(), name='google_callback'),
    path('reset-password/request/', views.PasswordResetRequestView.as_view(), name='reset_password_request'),
    path('verify-password/request/', views.ResetPasswordrequestVerifyView.as_view(), name='reset_password_verify'),
    path('update-password/', views.RequestUpdatePasswordView.as_view(), name='request_update_password'),
]
