from django.core.management.base import BaseCommand
from core.models import Course, Lesson, Exercise, ExerciseChoice


class Command(BaseCommand):
    help = 'Populate the database with sample language learning data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Populating sample data...')

        Course.objects.all().delete()

        chinese_course = Course.objects.create(
            title='Chinese to English (Basics)',
            slug='zh-en-basics',
            from_language='Chinese',
            to_language='English',
            description='Greetings and simple phrases.'
        )

        lesson1 = Lesson.objects.create(
            course=chinese_course,
            title='Greetings',
            order=1
        )

        ex1 = Exercise.objects.create(
            lesson=lesson1,
            order=1,
            type=Exercise.TRANSLATE,
            prompt='你好',
            answer_text='hello'
        )

        ex2 = Exercise.objects.create(
            lesson=lesson1,
            order=2,
            type=Exercise.MULTIPLE_CHOICE,
            prompt='谢谢',
            answer_text='thank you'
        )
        ExerciseChoice.objects.create(exercise=ex2, text='goodbye', is_correct=False)
        ExerciseChoice.objects.create(exercise=ex2, text='thank you', is_correct=True)
        ExerciseChoice.objects.create(exercise=ex2, text='please', is_correct=False)

        spanish_course = Course.objects.create(
            title='Learn English from Spanish',
            slug='spanish-to-english',
            from_language='Spanish',
            to_language='English',
            description='Learn English essentials with lessons tailored for Spanish speakers.'
        )

        es_lesson1 = Lesson.objects.create(
            course=spanish_course,
            title='Basic Greetings',
            order=1
        )

        es_ex1 = Exercise.objects.create(
            lesson=es_lesson1,
            order=1,
            type=Exercise.TRANSLATE,
            prompt='Hello',
            answer_text='Hello'
        )

        french_course = Course.objects.create(
            title='Learn English from French',
            slug='french-to-english',
            from_language='French',
            to_language='English',
            description='Comprehensive English lessons for French speakers at all levels.'
        )

        fr_lesson1 = Lesson.objects.create(
            course=french_course,
            title='Salutations',
            order=1
        )

        fr_ex1 = Exercise.objects.create(
            lesson=fr_lesson1,
            order=1,
            type=Exercise.TRANSLATE,
            prompt='Hello',
            answer_text='Hello'
        )

        self.stdout.write(self.style.SUCCESS('Successfully populated sample data!'))
        self.stdout.write(f'Created {Course.objects.count()} courses')
        self.stdout.write(f'Created {Lesson.objects.count()} lessons')
        self.stdout.write(f'Created {Exercise.objects.count()} exercises')
