from django.shortcuts import render
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Lesson
from .serializers import LessonSerializer

# Create your views here.

class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Only return lessons created by the current user
        return self.queryset.filter(created_by=self.request.user)

    def perform_create(self, serializer):
        # The created_by field is automatically set in the serializer
        serializer.save()

    @action(detail=True, methods=['post'])
    def upload_image(self, request, pk=None):
        lesson = self.get_object()
        if 'image' in request.FILES:
            lesson.image = request.FILES['image']
            lesson.save()
            return Response({'status': 'image uploaded'})
        return Response({'status': 'no image provided'}, status=400)

    @action(detail=True, methods=['post'])
    def upload_audio(self, request, pk=None):
        lesson = self.get_object()
        if 'audio' in request.FILES:
            lesson.audio = request.FILES['audio']
            lesson.save()
            return Response({'status': 'audio uploaded'})
        return Response({'status': 'no audio provided'}, status=400)
