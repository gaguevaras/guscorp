from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LessonViewSet, PracticeSessionViewSet

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
] 