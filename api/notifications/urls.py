# urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EmailTemplateViewSet,
    EmailAttachmentViewSet,
    EmailImageViewSet,
    EmailStyleViewSet,
    AdminSendEmailView,
    GroupTargetingView
)

router = DefaultRouter()
router.register('templates', EmailTemplateViewSet)
router.register('attachments', EmailAttachmentViewSet)
router.register('images', EmailImageViewSet)
router.register('styles', EmailStyleViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('send-email/', AdminSendEmailView.as_view(), name='send-template-email'),
    path('group-targeting/', GroupTargetingView.as_view(), name='group-targeting'),
]
