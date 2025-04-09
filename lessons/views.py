from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Lesson, LessonAssignment, PracticeSession
from .serializers import (
    LessonSerializer, 
    LessonAssignmentSerializer,
    PracticeSessionSerializer
)
from django.db import models

# Create your views here.

class PracticeSessionViewSet(viewsets.ModelViewSet):
    serializer_class = PracticeSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        lesson_id = self.kwargs.get('lesson_id')
        return PracticeSession.objects.filter(
            user=self.request.user,
            lesson_id=lesson_id
        )

    def perform_create(self, serializer):
        lesson_id = self.kwargs.get('lesson_id')
        serializer.save(
            user=self.request.user,
            lesson_id=lesson_id
        )

    @action(detail=False, methods=['get'])
    def by_lesson(self, request, lesson_id=None):
        practice_sessions = PracticeSession.objects.filter(
            user=request.user,
            lesson_id=lesson_id
        )
        serializer = self.get_serializer(practice_sessions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def upload_audio(self, request, lesson_id=None, pk=None):
        practice_session = self.get_object()
        if 'audio' in request.FILES:
            practice_session.audio = request.FILES['audio']
            practice_session.save()
            return Response({'status': 'audio uploaded'})
        return Response({'status': 'no audio provided'}, status=400)

class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Return lessons created by the current user OR assigned to the current user
        return Lesson.objects.filter(
            models.Q(created_by=self.request.user) |
            models.Q(assignments__assigned_to=self.request.user)
        ).distinct()

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        lesson = self.get_object()
        serializer = LessonAssignmentSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            # Check if the lesson is already assigned to this user
            if LessonAssignment.objects.filter(
                lesson=lesson,
                assigned_to=serializer.validated_data['assigned_to']
            ).exists():
                return Response(
                    {'error': 'This lesson is already assigned to this user'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Add the lesson to the validated data
            serializer.validated_data['lesson'] = lesson
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def assignments(self, request, pk=None):
        lesson = self.get_object()
        assignments = lesson.assignments.all()
        serializer = LessonAssignmentSerializer(assignments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def assigned_to_me(self, request):
        assigned_lessons = Lesson.objects.filter(
            assignments__assigned_to=request.user
        ).distinct()
        serializer = self.get_serializer(assigned_lessons, many=True)
        return Response(serializer.data)

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
