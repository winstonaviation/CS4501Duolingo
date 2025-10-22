from django.core.management.base import BaseCommand
from core.models import Course, Section, Unit, Lesson, Exercise, ExerciseChoice, DailyQuest


class Command(BaseCommand):
    help = 'Populate the database with Spanish demo content matching Duolingo UI'

    def handle(self, *args, **kwargs):
        self.stdout.write('Populating Spanish demo data...')

        # Get or create Spanish course
        spanish_course, created = Course.objects.get_or_create(
            slug='spanish-to-english',
            defaults={
                'title': 'Learn English from Spanish',
                'from_language': 'Spanish',
                'to_language': 'English',
                'description': 'Learn English essentials with lessons tailored for Spanish speakers.'
            }
        )

        # Create Section 1
        section1, _ = Section.objects.get_or_create(
            course=spanish_course,
            order=1,
            defaults={
                'title': 'Getting Started',
                'description': 'Master the basics'
            }
        )

        # Create Unit 1
        unit1, _ = Unit.objects.get_or_create(
            section=section1,
            order=1,
            defaults={
                'title': 'Form basic sentences',
                'description': 'Learn to introduce yourself and describe people'
            }
        )

        # Lesson 1: Basic Nouns
        lesson1, _ = Lesson.objects.get_or_create(
            unit=unit1,
            order=1,
            defaults={
                'title': 'Basic Nouns',
                'lesson_type': Lesson.LESSON,
                'is_locked': False
            }
        )

        # Exercise 1: "Which one of these is 'the boy'?" (like the screenshot)
        ex1, _ = Exercise.objects.get_or_create(
            lesson=lesson1,
            order=1,
            defaults={
                'type': Exercise.MULTIPLE_CHOICE,
                'prompt': 'the boy',
                'answer_text': 'el niño',
                'is_new_word': True,
                'hint': 'In Spanish, nouns have gender. "Niño" is masculine.'
            }
        )

        # Add choices for visual multiple choice (note: without actual images, we use text)
        choices_data = [
            {'text': 'el niño', 'is_correct': True},
            {'text': 'la niña', 'is_correct': False},
            {'text': 'la mujer', 'is_correct': False},
        ]

        for idx, choice_data in enumerate(choices_data, 1):
            ExerciseChoice.objects.get_or_create(
                exercise=ex1,
                text=choice_data['text'],
                defaults={'is_correct': choice_data['is_correct']}
            )

        # Exercise 2: "Which one of these is 'the girl'?"
        ex2, _ = Exercise.objects.get_or_create(
            lesson=lesson1,
            order=2,
            defaults={
                'type': Exercise.MULTIPLE_CHOICE,
                'prompt': 'the girl',
                'answer_text': 'la niña',
                'is_new_word': True,
                'hint': 'In Spanish, feminine nouns use "la".'
            }
        )

        choices_data2 = [
            {'text': 'el niño', 'is_correct': False},
            {'text': 'la niña', 'is_correct': True},
            {'text': 'el hombre', 'is_correct': False},
        ]

        for choice_data in choices_data2:
            ExerciseChoice.objects.get_or_create(
                exercise=ex2,
                text=choice_data['text'],
                defaults={'is_correct': choice_data['is_correct']}
            )

        # Exercise 3: Translation exercise
        ex3, _ = Exercise.objects.get_or_create(
            lesson=lesson1,
            order=3,
            defaults={
                'type': Exercise.TRANSLATE,
                'prompt': 'la mujer',
                'answer_text': 'the woman',
                'hint': 'Mujer means woman in Spanish.'
            }
        )

        # Exercise 4: "Which one is 'the man'?"
        ex4, _ = Exercise.objects.get_or_create(
            lesson=lesson1,
            order=4,
            defaults={
                'type': Exercise.MULTIPLE_CHOICE,
                'prompt': 'the man',
                'answer_text': 'el hombre',
                'is_new_word': False
            }
        )

        choices_data4 = [
            {'text': 'el hombre', 'is_correct': True},
            {'text': 'la mujer', 'is_correct': False},
            {'text': 'el niño', 'is_correct': False},
        ]

        for choice_data in choices_data4:
            ExerciseChoice.objects.get_or_create(
                exercise=ex4,
                text=choice_data['text'],
                defaults={'is_correct': choice_data['is_correct']}
            )

        # Exercise 5: Simple translation
        ex5, _ = Exercise.objects.get_or_create(
            lesson=lesson1,
            order=5,
            defaults={
                'type': Exercise.TRANSLATE,
                'prompt': 'el niño y la niña',
                'answer_text': 'the boy and the girl',
                'hint': 'Y means "and" in Spanish.'
            }
        )

        # Lesson 2: Greetings
        lesson2, _ = Lesson.objects.get_or_create(
            unit=unit1,
            order=2,
            defaults={
                'title': 'Greetings',
                'lesson_type': Lesson.LESSON,
                'is_locked': False
            }
        )

        # Add some greeting exercises
        greeting_exercises = [
            {
                'order': 1,
                'type': Exercise.MULTIPLE_CHOICE,
                'prompt': 'How do you say "hello" in Spanish?',
                'answer_text': 'hola',
                'is_new_word': True,
                'choices': [
                    {'text': 'hola', 'is_correct': True},
                    {'text': 'adiós', 'is_correct': False},
                    {'text': 'gracias', 'is_correct': False},
                ]
            },
            {
                'order': 2,
                'type': Exercise.TRANSLATE,
                'prompt': 'buenos días',
                'answer_text': 'good morning',
                'is_new_word': True,
                'hint': 'Buenos means good, días means days'
            },
            {
                'order': 3,
                'type': Exercise.TRANSLATE,
                'prompt': 'how are you?',
                'answer_text': '¿cómo estás?',
                'is_new_word': False,
            },
        ]

        for ex_data in greeting_exercises:
            choices_data = ex_data.pop('choices', None)
            ex, _ = Exercise.objects.get_or_create(
                lesson=lesson2,
                order=ex_data['order'],
                defaults={
                    'type': ex_data['type'],
                    'prompt': ex_data['prompt'],
                    'answer_text': ex_data['answer_text'],
                    'is_new_word': ex_data.get('is_new_word', False),
                    'hint': ex_data.get('hint', ''),
                }
            )

            if choices_data:
                for choice_data in choices_data:
                    ExerciseChoice.objects.get_or_create(
                        exercise=ex,
                        text=choice_data['text'],
                        defaults={'is_correct': choice_data['is_correct']}
                    )

        # Create Unit 2
        unit2, _ = Unit.objects.get_or_create(
            section=section1,
            order=2,
            defaults={
                'title': 'Get around in a city',
                'description': 'Learn vocabulary for navigating urban environments'
            }
        )

        # Add a locked lesson as an example
        lesson3, _ = Lesson.objects.get_or_create(
            unit=unit2,
            order=1,
            defaults={
                'title': 'Places in the City',
                'lesson_type': Lesson.LESSON,
                'is_locked': True
            }
        )

        # Create daily quests if they don't exist
        quests_data = [
            {
                'quest_type': DailyQuest.EARN_XP,
                'title': 'Earn 10 XP',
                'description': 'Complete lessons to earn experience points',
                'target_value': 10,
                'xp_reward': 10,
                'gem_reward': 0,
            },
            {
                'quest_type': DailyQuest.COMPLETE_LESSONS,
                'title': 'Complete 3 lessons',
                'description': 'Finish three complete lessons today',
                'target_value': 3,
                'xp_reward': 20,
                'gem_reward': 5,
            },
            {
                'quest_type': DailyQuest.PERFECT_LESSON,
                'title': 'Get a perfect lesson',
                'description': 'Complete a lesson with no mistakes',
                'target_value': 1,
                'xp_reward': 15,
                'gem_reward': 10,
            },
        ]

        for quest_data in quests_data:
            DailyQuest.objects.get_or_create(
                quest_type=quest_data['quest_type'],
                defaults=quest_data
            )

        self.stdout.write(self.style.SUCCESS('Successfully populated Spanish demo data!'))
        self.stdout.write(f'Created course: {spanish_course.title}')
        self.stdout.write(f'Created {Section.objects.filter(course=spanish_course).count()} sections')
        self.stdout.write(f'Created {Unit.objects.filter(section__course=spanish_course).count()} units')
        self.stdout.write(f'Created {Lesson.objects.filter(unit__section__course=spanish_course).count()} lessons')
        self.stdout.write(f'Created {Exercise.objects.filter(lesson__unit__section__course=spanish_course).count()} exercises')
        self.stdout.write(f'Created {DailyQuest.objects.count()} daily quests')