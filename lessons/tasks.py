from celery import shared_task
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
import numpy as np
import logging
from .models import PracticeSession
from .audio_compare import compare_audio

logger = logging.getLogger(__name__)

def convert_numpy_to_python(obj):
    """
    Convert numpy types to Python native types for JSON serialization.
    """
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_to_python(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_to_python(item) for item in obj]
    return obj

@shared_task
def process_practice_session_file(practice_audio_path, lesson_audio_path):
    """
    Process the uploaded audio file for a practice session and compare it with the lesson's audio.
    This function:
    1. Gets the absolute paths of both audio files
    2. Uses the compare_audio function to analyze the performance
    3. Updates the practice session with processing results
    """
    try:
        # Get the practice session associated with this file
        practice_session = PracticeSession.objects.get(audio=practice_audio_path)
        logger.info(f"Processing practice session {practice_session.id}")
        
        # Update processing status
        practice_session.processing_status = 'processing'
        practice_session.save()
        
        # Get absolute paths for both files
        practice_audio_abs = os.path.join(default_storage.location, practice_audio_path)
        lesson_audio_abs = os.path.join(default_storage.location, lesson_audio_path) if lesson_audio_path else None
        
        if not lesson_audio_abs or not os.path.exists(lesson_audio_abs):
            raise FileNotFoundError("Lesson audio file not found")
            
        # Use the compare_audio function to analyze the performance
        results = compare_audio(lesson_audio_abs, practice_audio_abs)
        logger.info(f"Audio comparison completed with results: {results}")
        
        # Convert numpy types to Python native types
        results = convert_numpy_to_python(results)
        
        # Prepare the processing results
        processing_results = {
            'overall_score': results['overall_score'],
            'pitch_accuracy': results['pitch_accuracy'],
            'timing_accuracy': results['timing_accuracy'],
            'harmonic_accuracy': results['harmonic_accuracy'],
            'details': results['details'],
            'results_dir': results['results_dir']
        }
        
        logger.info(f"Updating practice session with results: {processing_results}")
        
        # Update the practice session with processing results
        practice_session.processing_status = 'completed'
        practice_session.processing_results = processing_results
        practice_session.save()
        
        # Verify the save
        practice_session.refresh_from_db()
        logger.info(f"Practice session updated. Current results: {practice_session.processing_results}")
        
        return {
            'status': 'success',
            'message': 'Audio comparison completed successfully',
            'practice_audio': practice_audio_path,
            'lesson_audio': lesson_audio_path,
            'results': results
        }
    except PracticeSession.DoesNotExist:
        logger.error(f"Practice session not found for file: {practice_audio_path}")
        return {
            'status': 'error',
            'message': f'Practice session not found for file: {practice_audio_path}'
        }
    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
        if 'practice_session' in locals():
            practice_session.processing_status = 'failed'
            practice_session.save()
        return {
            'status': 'error',
            'message': str(e)
        }
    except Exception as e:
        logger.error(f"Error processing files: {str(e)}")
        # Update practice session status to failed
        if 'practice_session' in locals():
            practice_session.processing_status = 'failed'
            practice_session.save()
            
        return {
            'status': 'error',
            'message': f'Error processing files: {str(e)}'
        } 