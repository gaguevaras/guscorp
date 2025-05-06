from rest_framework import serializers
from .models import Lesson, LessonAssignment, PracticeSession, LessonAssignmentRequest
from accounts.serializers import UserProfileSerializer
from accounts.models import CustomUser

class PracticeSessionSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)
    lesson_name = serializers.CharField(source='lesson.name', read_only=True)

    class Meta:
        model = PracticeSession
        fields = [
            'id', 'lesson', 'lesson_name', 'user', 'audio', 'difficulty',
            'notes', 'created_at', 'updated_at', 'processing_status', 'processing_results'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at', 'lesson', 'processing_status', 'processing_results']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class LessonAssignmentSerializer(serializers.ModelSerializer):
    assigned_to = UserProfileSerializer(read_only=True)
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(),
        write_only=True,
        source='assigned_to'
    )

    class Meta:
        model = LessonAssignment
        fields = ['id', 'lesson', 'assigned_by', 'assigned_to', 'assigned_to_id', 'assigned_at', 'due_date', 'notes']
        read_only_fields = ['assigned_by', 'assigned_at', 'lesson', 'assigned_to']

    def create(self, validated_data):
        validated_data['assigned_by'] = self.context['request'].user
        return super().create(validated_data)

class LessonAssignmentRequestSerializer(serializers.ModelSerializer):
    requested_to = UserProfileSerializer(read_only=True)
    requested_to_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(),
        write_only=True,
        source='requested_to'
    )
    requested_by = UserProfileSerializer(read_only=True)
    lesson_details = serializers.SerializerMethodField()
    lesson_id = serializers.PrimaryKeyRelatedField(
        queryset=Lesson.objects.all(),
        write_only=True,
        source='lesson'
    )

    class Meta:
        model = LessonAssignmentRequest
        fields = [
            'id', 'lesson_id', 'lesson_details', 'requested_by', 'requested_to',
            'requested_to_id', 'status', 'due_date', 'notes', 'created_at',
            'updated_at'
        ]
        read_only_fields = ['requested_by', 'created_at', 'updated_at', 'status']

    def get_lesson_details(self, obj):
        from .serializers import LessonSerializer
        return LessonSerializer(obj.lesson, context=self.context).data

    def create(self, validated_data):
        validated_data['requested_by'] = self.context['request'].user
        return super().create(validated_data)

class LessonSerializer(serializers.ModelSerializer):
    assignments = serializers.SerializerMethodField()
    practice_sessions = PracticeSessionSerializer(many=True, read_only=True)
    is_assigned_to_me = serializers.SerializerMethodField()
    my_practice_sessions = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = [
            'id', 'name', 'category', 'instructions', 'frequency',
            'image', 'audio', 'created_by', 'created_at', 'updated_at',
            'assignments', 'practice_sessions', 'is_assigned_to_me',
            'my_practice_sessions'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def get_is_assigned_to_me(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.assignments.filter(assigned_to=request.user).exists()
        return False

    def get_assignments(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            assignments = obj.assignments.filter(assigned_by=request.user)
            return LessonAssignmentSerializer(assignments, many=True).data
        return []

    def get_my_practice_sessions(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return PracticeSessionSerializer(
                obj.practice_sessions.filter(user=request.user),
                many=True,
                context=self.context
            ).data
        return []

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data) 