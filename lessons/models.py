from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator

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
