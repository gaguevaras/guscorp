from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError

class Lesson(models.Model):
    CATEGORY_CHOICES = [
        ('technique', 'Technique'),
        ('scales', 'Scales'),
        ('repertory', 'Repertory'),
        ('theory', 'Theory'),
        ('ear_training', 'Ear Training'),
        ('other', 'Other'),
    ]

    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('twice_daily', 'Twice Daily'),
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-Weekly'),
        ('monthly', 'Monthly'),
    ]

    name = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    instructions = models.TextField()
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    image = models.ImageField(upload_to='lesson_images/', blank=True, null=True)
    audio = models.FileField(
        upload_to='lesson_audio/',
        validators=[FileExtensionValidator(allowed_extensions=['mp3', 'wav', 'ogg', 'm4a'])],
        blank=True,
        null=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='lessons'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"

class PracticeSession(models.Model):
    DIFFICULTY_CHOICES = [
        (1, 'Very Easy'),
        (2, 'Easy'),
        (3, 'Moderate'),
        (4, 'Challenging'),
        (5, 'Very Difficult'),
    ]

    PROCESSING_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='practice_sessions'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='practice_sessions'
    )
    audio = models.FileField(
        upload_to='practice_audio/',
        validators=[FileExtensionValidator(allowed_extensions=['mp3', 'wav', 'ogg', 'm4a'])],
        blank=True,
        null=True
    )
    difficulty = models.IntegerField(
        choices=DIFFICULTY_CHOICES,
        help_text='Rating from 1 (Very Easy) to 5 (Very Difficult)'
    )
    notes = models.TextField(blank=True)
    processing_status = models.CharField(
        max_length=20,
        choices=PROCESSING_STATUS_CHOICES,
        default='pending'
    )
    processing_results = models.JSONField(
        blank=True,
        null=True,
        help_text='Stores results from audio processing (duration, format, etc.)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.lesson.name} ({self.get_difficulty_display()})"

class LessonAssignment(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='assignments')
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assigned_lessons'
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_lessons'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['lesson', 'assigned_to']

    def __str__(self):
        return f"{self.lesson.name} assigned to {self.assigned_to.username}"

class LessonAssignmentRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='assignment_requests')
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_lesson_requests'
    )
    requested_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_lesson_requests'
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending'
    )
    due_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['lesson', 'requested_to']
        ordering = ['-created_at']

    def clean(self):
        if self.requested_by == self.requested_to:
            raise ValidationError("A user cannot request a lesson assignment to themselves.")
        if LessonAssignment.objects.filter(lesson=self.lesson, assigned_to=self.requested_to).exists():
            raise ValidationError("This lesson is already assigned to the user.")
        if self.status == 'pending' and LessonAssignmentRequest.objects.filter(
            lesson=self.lesson,
            requested_to=self.requested_to,
            status='pending'
        ).exists():
            raise ValidationError("A pending request for this lesson already exists for this user.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def accept(self):
        if self.status == 'pending':
            self.status = 'accepted'
            self.save()
            # Create the lesson assignment
            LessonAssignment.objects.create(
                lesson=self.lesson,
                assigned_by=self.requested_by,
                assigned_to=self.requested_to,
                due_date=self.due_date,
                notes=self.notes
            )

    def reject(self):
        if self.status == 'pending':
            self.status = 'rejected'
            self.save()

    def __str__(self):
        return f"{self.lesson.name} request from {self.requested_by.email} to {self.requested_to.email} ({self.status})"
