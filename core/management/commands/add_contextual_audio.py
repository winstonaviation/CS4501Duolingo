from django.core.management.base import BaseCommand
from django.db.models import Max
from core.models import Lesson, Exercise, ExerciseChoice
from gtts import gTTS
import os
from django.conf import settings
import random


class Command(BaseCommand):
    help = 'Add contextual audio exercises based on existing lesson content'

    def add_arguments(self, parser):
        parser.add_argument(
            '--lesson',
            type=int,
            help='Add audio exercises only to a specific lesson ID',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be added without actually adding',
        )

    def handle(self, *args, **kwargs):
        lesson_id = kwargs.get('lesson')
        dry_run = kwargs.get('dry_run')

        # Language code mapping for gTTS
        language_codes = {
            'spanish-to-english': 'es',
            'chinese-to-english': 'zh-CN',
            'zh-en-basics': 'zh-CN',
            'french-to-english': 'fr',
        }

        # Get lessons to process
        if lesson_id:
            lessons = Lesson.objects.filter(id=lesson_id)
        else:
            lessons = Lesson.objects.filter(
                unit__section__course__slug__in=language_codes.keys()
            )

        if not lessons.exists():
            self.stdout.write(self.style.WARNING('No lessons found'))
            return

        # Ensure media directory exists
        media_root = settings.MEDIA_ROOT
        audio_dir = os.path.join(media_root, 'exercise_audio')
        if not dry_run:
            os.makedirs(audio_dir, exist_ok=True)

        added_count = 0
        skipped_count = 0

        for lesson in lessons:
            self.stdout.write(f'\n{"="*60}')
            self.stdout.write(f'Analyzing Lesson: {lesson.title} (ID: {lesson.id})')
            self.stdout.write(f'{"="*60}')

            # Get course and language
            course_slug = lesson.unit.section.course.slug if lesson.unit else ''
            lang_code = language_codes.get(course_slug)
            
            if not lang_code:
                self.stdout.write(self.style.WARNING(
                    f'Unknown language for course: {course_slug}'
                ))
                skipped_count += 1
                continue

            # Analyze existing exercises in this lesson
            existing_exercises = lesson.exercises.all()
            
            # Extract vocabulary from existing exercises
            vocabulary = self._extract_vocabulary(existing_exercises)
            
            self.stdout.write(f'Found {len(vocabulary)} vocabulary items:')
            for item in vocabulary[:10]:  # Show first 10
                self.stdout.write(f'  - {item["prompt"]} → {item["answer"]}')
            if len(vocabulary) > 10:
                self.stdout.write(f'  ... and {len(vocabulary) - 10} more')

            # Generate audio exercises based on lesson content
            audio_exercises = self._generate_audio_exercises(
                vocabulary, 
                lang_code,
                existing_exercises
            )

            if not audio_exercises:
                self.stdout.write(self.style.WARNING(
                    'No suitable content found for audio exercises'
                ))
                skipped_count += 1
                continue

            # Get the highest order number for this lesson
            max_order = existing_exercises.aggregate(
                max_order=Max('order')
            )['max_order'] or 0

            # Add the generated exercises
            for idx, ex_data in enumerate(audio_exercises, start=1):
                if dry_run:
                    self.stdout.write(self.style.SUCCESS(
                        f'[DRY RUN] Would add {ex_data["type"]} exercise: "{ex_data["answer_text"]}"'
                    ))
                    if ex_data.get('word_bank'):
                        self.stdout.write(f'  Word bank: {", ".join(ex_data["word_bank"])}')
                    added_count += 1
                    continue

                # Check if similar exercise already exists
                existing = lesson.exercises.filter(
                    answer_text=ex_data['answer_text'],
                    type__in=[Exercise.LISTEN, Exercise.LISTEN_CONSTRUCT]
                ).first()

                if existing:
                    self.stdout.write(self.style.WARNING(
                        f'Skipping: Exercise with "{ex_data["answer_text"]}" already exists'
                    ))
                    skipped_count += 1
                    continue

                # Create exercise
                try:
                    exercise = Exercise.objects.create(
                        lesson=lesson,
                        order=max_order + idx,
                        type=ex_data['type'],
                        prompt=ex_data['prompt'],
                        answer_text=ex_data['answer_text'],
                        hint=ex_data.get('hint', ''),
                        is_new_word=ex_data.get('is_new_word', False),
                    )

                    # Generate audio file
                    filename = f'exercise_{exercise.id}.mp3'
                    filepath = os.path.join(audio_dir, filename)

                    tts = gTTS(text=ex_data['answer_text'], lang=lang_code, slow=False)
                    tts.save(filepath)

                    exercise.audio_file = f'exercise_audio/{filename}'
                    exercise.save()

                    self.stdout.write(self.style.SUCCESS(
                        f'✓ Added {ex_data["type"]} exercise: "{ex_data["answer_text"]}"'
                    ))
                    added_count += 1

                    # Create word bank choices if provided
                    if ex_data.get('word_bank'):
                        answer_words = ex_data['answer_text'].split()
                        for word in ex_data['word_bank']:
                            is_correct = word in answer_words
                            ExerciseChoice.objects.create(
                                exercise=exercise,
                                text=word,
                                is_correct=is_correct,
                            )
                        self.stdout.write(f'  Added word bank: {", ".join(ex_data["word_bank"])}')

                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f'✗ Error creating exercise: {str(e)}'
                    ))
                    if not dry_run and 'exercise' in locals():
                        exercise.delete()
                    skipped_count += 1

        # Summary
        self.stdout.write(self.style.SUCCESS(f'\n{"="*60}'))
        self.stdout.write(self.style.SUCCESS('Summary'))
        self.stdout.write(self.style.SUCCESS(f'{"="*60}'))
        self.stdout.write(f'Added: {added_count}')
        self.stdout.write(f'Skipped: {skipped_count}')
        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a dry run. No changes were made.'))
            self.stdout.write('Run without --dry-run to actually add exercises.')

    def _extract_vocabulary(self, exercises):
        """
        Extract vocabulary from existing exercises in the lesson.
        Returns list of dicts with prompt, answer, and metadata.
        """
        vocabulary = []
        
        for ex in exercises:
            # Skip exercises that are already audio-based
            if ex.type in [Exercise.LISTEN, Exercise.LISTEN_CONSTRUCT]:
                continue
            
            # Extract from translation exercises
            if ex.type == Exercise.TRANSLATE:
                vocabulary.append({
                    'prompt': ex.prompt,
                    'answer': ex.answer_text,
                    'type': 'translate',
                    'hint': ex.hint,
                    'is_new_word': ex.is_new_word,
                })
            
            # Extract from multiple choice
            elif ex.type == Exercise.MULTIPLE_CHOICE:
                vocabulary.append({
                    'prompt': ex.prompt,
                    'answer': ex.answer_text,
                    'type': 'multiple_choice',
                    'hint': ex.hint,
                    'is_new_word': ex.is_new_word,
                    'choices': [choice.text for choice in ex.choices.all()],
                })
        
        return vocabulary

    def _generate_audio_exercises(self, vocabulary, lang_code, existing_exercises):
        """
        Generate audio exercises based on lesson vocabulary.
        Creates both Listen & Type and Listen & Construct exercises.
        """
        if not vocabulary:
            return []
        
        audio_exercises = []
        
        # Strategy 1: Create Listen & Type for individual vocabulary items
        # Take words/phrases that are marked as new or important
        new_words = [v for v in vocabulary if v.get('is_new_word')]
        if new_words:
            # Add 1-2 Listen & Type exercises for new vocabulary
            for vocab_item in new_words[:2]:
                audio_exercises.append({
                    'type': Exercise.LISTEN,
                    'prompt': 'Type what you hear',
                    'answer_text': vocab_item['answer'],
                    'hint': vocab_item.get('hint', ''),
                    'is_new_word': True,
                })
        
        # Strategy 2: Create Listen & Construct for phrases/sentences
        # Look for multi-word answers (phrases or sentences)
        phrases = [v for v in vocabulary if len(v['answer'].split()) >= 2]
        
        if phrases:
            # Pick 1-2 phrases for word bank exercises
            selected_phrases = random.sample(phrases, min(2, len(phrases)))
            
            for phrase_item in selected_phrases:
                answer_words = phrase_item['answer'].split()
                
                # Create word bank with correct words + distractors
                word_bank = answer_words.copy()
                
                # Add distractors from other vocabulary in the lesson
                all_words = []
                for v in vocabulary:
                    all_words.extend(v['answer'].split())
                
                # Remove duplicates and get unique words
                unique_words = list(set(all_words))
                
                # Add 2-4 distractor words
                distractors = [w for w in unique_words if w not in answer_words]
                word_bank.extend(random.sample(distractors, min(3, len(distractors))))
                
                # Shuffle word bank
                random.shuffle(word_bank)
                
                audio_exercises.append({
                    'type': Exercise.LISTEN_CONSTRUCT,
                    'prompt': 'Tap what you hear',
                    'answer_text': phrase_item['answer'],
                    'hint': phrase_item.get('hint', 'Listen carefully and build the sentence'),
                    'is_new_word': False,
                    'word_bank': word_bank,
                })
        
        # Strategy 3: If no suitable content, create simple listen exercises
        if not audio_exercises and vocabulary:
            # Just create Listen & Type for any available vocabulary
            for vocab_item in vocabulary[:2]:
                audio_exercises.append({
                    'type': Exercise.LISTEN,
                    'prompt': 'Type what you hear',
                    'answer_text': vocab_item['answer'],
                    'hint': vocab_item.get('hint', ''),
                    'is_new_word': False,
                })
        
        return audio_exercises