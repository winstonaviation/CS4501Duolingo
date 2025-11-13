from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Exercise, ExerciseChoice
from gtts import gTTS
import os


class Command(BaseCommand):
    help = 'Generate audio files for exercises using Google Text-to-Speech'

    def add_arguments(self, parser):
        parser.add_argument(
            '--lesson',
            type=int,
            help='Generate audio only for a specific lesson ID',
        )
        parser.add_argument(
            '--exercise',
            type=int,
            help='Generate audio only for a specific exercise ID',
        )
        parser.add_argument(
            '--language',
            type=str,
            default='en',
            help='Language code for TTS (e.g., en, es, zh-CN, fr)',
        )
        parser.add_argument(
            '--regenerate',
            action='store_true',
            help='Regenerate audio even if file already exists',
        )

    def handle(self, *args, **kwargs):
        lesson_id = kwargs.get('lesson')
        exercise_id = kwargs.get('exercise')
        language = kwargs.get('language')
        regenerate = kwargs.get('regenerate')

        # Build query
        exercises = Exercise.objects.all()
        
        if lesson_id:
            exercises = exercises.filter(lesson_id=lesson_id)
            self.stdout.write(f'Filtering by lesson ID: {lesson_id}')
        
        if exercise_id:
            exercises = exercises.filter(id=exercise_id)
            self.stdout.write(f'Filtering by exercise ID: {exercise_id}')

        # Filter for exercises that need audio
        # Listen exercises and Listen & Construct exercises need audio
        exercises = exercises.filter(type__in=[Exercise.LISTEN, Exercise.LISTEN_CONSTRUCT])

        self.stdout.write(f'Found {exercises.count()} exercises to process')

        # Ensure media directories exist
        media_root = settings.MEDIA_ROOT
        audio_dir = os.path.join(media_root, 'exercise_audio')
        os.makedirs(audio_dir, exist_ok=True)

        generated_count = 0
        skipped_count = 0
        error_count = 0

        for exercise in exercises:
            # Check if audio already exists
            if exercise.audio_file and not regenerate:
                audio_path = os.path.join(media_root, exercise.audio_file.name)
                if os.path.exists(audio_path):
                    self.stdout.write(self.style.WARNING(
                        f'Skipping Exercise {exercise.id}: Audio already exists'
                    ))
                    skipped_count += 1
                    continue

            try:
                # Use answer_text for the audio (this is what they should hear)
                text = exercise.answer_text or exercise.prompt
                
                if not text:
                    self.stdout.write(self.style.WARNING(
                        f'Skipping Exercise {exercise.id}: No text to convert'
                    ))
                    skipped_count += 1
                    continue

                # Generate audio file
                filename = f'exercise_{exercise.id}.mp3'
                filepath = os.path.join(audio_dir, filename)

                # Create TTS object and save
                tts = gTTS(text=text, lang=language, slow=False)
                tts.save(filepath)

                # Update exercise with audio file path
                exercise.audio_file = f'exercise_audio/{filename}'
                exercise.save()

                self.stdout.write(self.style.SUCCESS(
                    f'✓ Generated audio for Exercise {exercise.id}: "{text[:50]}..."'
                ))
                generated_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'✗ Error generating audio for Exercise {exercise.id}: {str(e)}'
                ))
                error_count += 1

        # Summary
        self.stdout.write(self.style.SUCCESS(f'\n{"="*60}'))
        self.stdout.write(self.style.SUCCESS(f'Audio Generation Complete!'))
        self.stdout.write(self.style.SUCCESS(f'{"="*60}'))
        self.stdout.write(f'Generated: {generated_count}')
        self.stdout.write(f'Skipped: {skipped_count}')
        self.stdout.write(f'Errors: {error_count}')
        self.stdout.write(f'Total processed: {generated_count + skipped_count + error_count}')