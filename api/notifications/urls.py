# urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmailTemplateViewSet

router = DefaultRouter()
router.register(r'emailtemplates', EmailTemplateViewSet, basename='emailtemplates')

urlpatterns = [
    path('', include(router.urls)),
]
urlpatterns += [
    path('emailtemplates/', EmailTemplateViewSet.as_view({'get': 'list', 'post': 'create'}), name='emailtemplate'),
    path('emailtemplates/<int:pk>/', EmailTemplateViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='emailtemplate-detail'),
]