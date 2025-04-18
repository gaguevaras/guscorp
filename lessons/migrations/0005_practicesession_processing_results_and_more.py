# Generated by Django 5.1.2 on 2025-04-12 23:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lessons', '0004_practicesession'),
    ]

    operations = [
        migrations.AddField(
            model_name='practicesession',
            name='processing_results',
            field=models.JSONField(blank=True, help_text='Stores results from audio processing (duration, format, etc.)', null=True),
        ),
        migrations.AddField(
            model_name='practicesession',
            name='processing_status',
            field=models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending', max_length=20),
        ),
    ]
