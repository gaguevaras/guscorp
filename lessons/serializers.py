from rest_framework import serializers
from .models import Lesson, LessonAssignment

class LessonAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonAssignment
        fields = ['id', 'lesson', 'assigned_by', 'assigned_to', 'assigned_at', 'due_date', 'notes']
        read_only_fields = ['assigned_by', 'assigned_at', 'lesson']

    def create(self, validated_data):
        validated_data['assigned_by'] = self.context['request'].user
        return super().create(validated_data)

class LessonSerializer(serializers.ModelSerializer):
    assignments = LessonAssignmentSerializer(many=True, read_only=True)
    is_assigned_to_me = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = [
            'id', 'name', 'category', 'instructions', 'frequency',
            'image', 'audio', 'created_by', 'created_at', 'updated_at',
            'assignments', 'is_assigned_to_me'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def get_is_assigned_to_me(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.assignments.filter(assigned_to=request.user).exists()
        return False

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data) 