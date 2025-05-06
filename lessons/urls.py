from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LessonViewSet, 
    PracticeSessionViewSet, 
    LessonAssignmentRequestViewSet,
    create_lesson_request,
    accept_lesson_request,
    reject_lesson_request
)

router = DefaultRouter()
router.register(r'', LessonViewSet, basename='lesson')

urlpatterns = [
    path('', include(router.urls)),
    path('<int:lesson_id>/practice/', PracticeSessionViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='lesson-practice-list'),
    path('<int:lesson_id>/practice/<int:pk>/', PracticeSessionViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='lesson-practice-detail'),
    path('<int:lesson_id>/practice/<int:pk>/upload_audio/', PracticeSessionViewSet.as_view({
        'post': 'upload_audio'
    }), name='lesson-practice-upload-audio'),
    path('<int:lesson_id>/practice/by_user/', PracticeSessionViewSet.as_view({
        'get': 'by_user'
    }), name='lesson-practice-by-user'),
    # Lesson request endpoints
    path('requests/create/', create_lesson_request, name='lesson-request-create'),
    path('requests/<int:pk>/accept/', accept_lesson_request, name='lesson-request-accept'),
    path('requests/<int:pk>/reject/', reject_lesson_request, name='lesson-request-reject'),
    path('requests/received/', LessonAssignmentRequestViewSet.as_view({
        'get': 'received'
    }), name='lesson-request-received'),
    path('requests/sent/', LessonAssignmentRequestViewSet.as_view({
        'get': 'sent'
    }), name='lesson-request-sent'),
    path('requests/assigned_to_me/', LessonAssignmentRequestViewSet.as_view({
        'get': 'assigned_to_me'
    }), name='lesson-request-assigned-to-me'),
    path('requests/<int:pk>/', LessonAssignmentRequestViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='lesson-request-detail'),
] 