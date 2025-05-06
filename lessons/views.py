from django.shortcuts import render
from rest_framework import viewsets, permissions, status, views
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from .models import Lesson, LessonAssignment, PracticeSession, LessonAssignmentRequest
from contacts.models import Contact
from .serializers import (
    LessonSerializer, 
    LessonAssignmentSerializer,
    PracticeSessionSerializer,
    LessonAssignmentRequestSerializer
)
from django.db import models
from .tasks import process_practice_session_file
from django.http import Http404
from accounts.models import CustomUser

# Create your views here.

class PracticeSessionViewSet(viewsets.ModelViewSet):
    serializer_class = PracticeSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        lesson_id = self.kwargs.get('lesson_id')
        # Return all practice sessions for the lesson
        return PracticeSession.objects.filter(lesson_id=lesson_id)

    def get_object(self):
        # Get the practice session
        practice_session = super().get_object()
        
        # Check if the current user is either:
        # 1. The author of the practice session, or
        # 2. The assigner of the lesson to the practice session's user
        if (practice_session.user == self.request.user or
            LessonAssignment.objects.filter(
                lesson=practice_session.lesson,
                assigned_by=self.request.user,
                assigned_to=practice_session.user
            ).exists()):
            return practice_session
            
        # If neither condition is met, raise 404
        raise Http404("Practice session not found")

    def perform_create(self, serializer):
        lesson_id = self.kwargs.get('lesson_id')
        serializer.save(
            user=self.request.user,
            lesson_id=lesson_id
        )

    @action(detail=False, methods=['get'])
    def by_lesson(self, request, lesson_id=None):
        # Only return practice sessions for the current user
        practice_sessions = PracticeSession.objects.filter(
            user=request.user,
            lesson_id=lesson_id
        )
        serializer = self.get_serializer(practice_sessions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_user(self, request, lesson_id=None):
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response(
                {'error': 'user_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if the current user has assigned this lesson to the requested user
        has_assigned = LessonAssignment.objects.filter(
            lesson_id=lesson_id,
            assigned_by=request.user,
            assigned_to_id=user_id
        ).exists()
        
        if not has_assigned:
            return Response(
                {'error': 'You can only view practice sessions of users you have assigned this lesson to'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        practice_sessions = PracticeSession.objects.filter(
            user_id=user_id,
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
            
            # Get the relative paths of both files
            practice_audio_path = practice_session.audio.name
            lesson_audio_path = practice_session.lesson.audio.name if practice_session.lesson.audio else None
            
            # Call the Celery task to process both files
            process_practice_session_file.delay(practice_audio_path, lesson_audio_path)
            
            return Response({
                'status': 'audio uploaded',
                'message': 'File is being processed'
            })
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

    @action(detail=False, methods=['get'])
    def assigned_by_me(self, request):
        assigned_lessons = Lesson.objects.filter(
            assignments__assigned_by=request.user
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

class LessonAssignmentRequestViewSet(viewsets.ModelViewSet):
    serializer_class = LessonAssignmentRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        # Return requests sent by or received by the current user
        return LessonAssignmentRequest.objects.filter(
            models.Q(requested_by=self.request.user) |
            models.Q(requested_to=self.request.user)
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user)

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        assignment_request = self.get_object()
        if assignment_request.requested_to != request.user:
            return Response(
                {'error': 'Only the recipient can accept a request'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        assignment_request.accept()
        return Response({'status': 'request accepted'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        assignment_request = self.get_object()
        if assignment_request.requested_to != request.user:
            return Response(
                {'error': 'Only the recipient can reject a request'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        assignment_request.reject()
        return Response({'status': 'request rejected'})

    @action(detail=False, methods=['get'])
    def sent(self, request):
        sent_requests = LessonAssignmentRequest.objects.filter(
            requested_by=request.user
        )
        serializer = self.get_serializer(sent_requests, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def received(self, request):
        received_requests = LessonAssignmentRequest.objects.filter(
            requested_to=request.user,
            status='pending'
        )
        serializer = self.get_serializer(received_requests, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def assigned_to_me(self, request):
        # Get all accepted requests that were assigned to me
        assigned_requests = LessonAssignmentRequest.objects.filter(
            requested_to=request.user,
            status='accepted'
        )
        serializer = self.get_serializer(assigned_requests, many=True)
        return Response(serializer.data)

@api_view(['POST'])
def create_lesson_request(request):
    """
    Create a new lesson assignment request.
    """
    # Check if lesson_id is provided
    lesson_id = request.data.get('lesson_id')
    if not lesson_id:
        return Response(
            {"error": "Lesson ID is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if requested_to_id is provided
    requested_to_id = request.data.get('requested_to_id')
    if not requested_to_id:
        return Response(
            {"error": "User ID to assign to is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Look up the lesson
    try:
        lesson = Lesson.objects.get(id=lesson_id)
    except Lesson.DoesNotExist:
        return Response(
            {"error": f"Lesson with ID {lesson_id} not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Look up the user
    try:
        requested_to = CustomUser.objects.get(id=requested_to_id)
    except CustomUser.DoesNotExist:
        return Response(
            {"error": f"User with ID {requested_to_id} not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if this is a request to yourself
    if requested_to.id == request.user.id:
        return Response(
            {"error": "You cannot assign a lesson to yourself"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if the lesson is already assigned
    existing_assignment = LessonAssignment.objects.filter(
        lesson=lesson,
        assigned_to=requested_to
    ).exists()
    
    if existing_assignment:
        return Response(
            {"error": "This lesson is already assigned to this user"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if there's a pending request already
    existing_request = LessonAssignmentRequest.objects.filter(
        lesson=lesson,
        requested_to=requested_to,
        status='pending'
    ).exists()
    
    if existing_request:
        return Response(
            {"error": "A pending request already exists for this lesson and user"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create the request
    serializer = LessonAssignmentRequestSerializer(
        data=request.data,
        context={'request': request}
    )
    
    if serializer.is_valid():
        serializer.save(requested_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def accept_lesson_request(request, pk):
    """
    Accept a lesson assignment request.
    """
    try:
        assignment_request = LessonAssignmentRequest.objects.get(
            id=pk,
            requested_to=request.user,
            status='pending'
        )
    except LessonAssignmentRequest.DoesNotExist:
        return Response(
            {"error": "Request not found or not in pending state"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    assignment_request.accept()
    return Response({"status": "request accepted"})

@api_view(['POST'])
def reject_lesson_request(request, pk):
    """
    Reject a lesson assignment request.
    """
    try:
        assignment_request = LessonAssignmentRequest.objects.get(
            id=pk,
            requested_to=request.user,
            status='pending'
        )
    except LessonAssignmentRequest.DoesNotExist:
        return Response(
            {"error": "Request not found or not in pending state"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    assignment_request.reject()
    return Response({"status": "request rejected"})
