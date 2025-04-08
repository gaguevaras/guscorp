from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ContactViewSet, 
    ContactRequestViewSet, 
    ContactRequestList, 
    create_contact_request,
    accept_contact_request,
    reject_contact_request
)

# Create a router for contacts
router = DefaultRouter()
router.register(r'', ContactViewSet, basename='contact')

urlpatterns = [
    path('', include(router.urls)),
    # Use dedicated function views
    path('requests/create/', create_contact_request, name='contact-request-create'),
    path('requests/<int:pk>/accept/', accept_contact_request, name='contact-request-accept'),
    path('requests/<int:pk>/reject/', reject_contact_request, name='contact-request-reject'),
    # Use APIView for GET list operations
    path('requests/', ContactRequestList.as_view(), name='contact-request-list'),
    # Add custom actions for list operations - these must come before parameterized paths
    path('requests/received/', ContactRequestViewSet.as_view({
        'get': 'received'
    }), name='contact-request-received'),
    path('requests/sent/', ContactRequestViewSet.as_view({
        'get': 'sent'
    }), name='contact-request-sent'),
    # Detail view should come last
    path('requests/<int:pk>/', ContactRequestViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='contact-request-detail'),
] 