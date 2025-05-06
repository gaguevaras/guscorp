from django.contrib import admin
from .models import Lesson, PracticeSession, LessonAssignment, LessonAssignmentRequest

@admin.register(LessonAssignmentRequest)
class LessonAssignmentRequestAdmin(admin.ModelAdmin):
    list_display = ('lesson', 'requested_by', 'requested_to', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('lesson__name', 'requested_by__email', 'requested_to__email')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

# Register other models if they're not already registered
admin.site.register(Lesson)
admin.site.register(PracticeSession)
admin.site.register(LessonAssignment)
