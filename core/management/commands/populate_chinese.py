from django.core.management.base import BaseCommand
from core.models import Course, Section, Unit, Lesson, Exercise, ExerciseChoice, DailyQuest


class Command(BaseCommand):
    help = 'Populate the database with Chinese demo content matching Multilingo UI'

    def handle(self, *args, **kwargs):
        self.stdout.write('Populating Chinese demo data...')

        # Get or create Chinese course
        chinese_course, created = Course.objects.get_or_create(
            slug='chinese-to-english',
            defaults={
                'title': 'Learn English from Chinese',
                'from_language': 'Chinese',
                'to_language': 'English',
                'description': 'Learn English essentials with lessons tailored for Chinese speakers.'
            }
        )

        # Create Section 1
        section1, _ = Section.objects.get_or_create(
            course=chinese_course,
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

        # Exercise 1: "Which one of these is 'the boy'?"
        ex1, _ = Exercise.objects.get_or_create(
            lesson=lesson1,
            order=1,
            defaults={
                'type': Exercise.MULTIPLE_CHOICE,
                'prompt': 'the boy',
                'answer_text': '男孩 (nánhái)',
                'is_new_word': True,
                'hint': 'In Chinese, 男 means male and 孩 means child.'
            }
        )

        # Add choices for visual multiple choice
        choices_data = [
            {'text': '男孩 (nánhái)', 'is_correct': True},
            {'text': '女孩 (nǚhái)', 'is_correct': False},
            {'text': '女人 (nǚrén)', 'is_correct': False},
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
                'answer_text': '女孩 (nǚhái)',
                'is_new_word': True,
                'hint': 'In Chinese, 女 means female and 孩 means child.'
            }
        )

        choices_data2 = [
            {'text': '男孩 (nánhái)', 'is_correct': False},
            {'text': '女孩 (nǚhái)', 'is_correct': True},
            {'text': '男人 (nánrén)', 'is_correct': False},
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
                'prompt': '女人 (nǚrén)',
                'answer_text': 'the woman',
                'hint': 'Woman in Chinese is 女人 (nǚrén).'
            }
        )

        # Exercise 4: "Which one is 'the man'?"
        ex4, _ = Exercise.objects.get_or_create(
            lesson=lesson1,
            order=4,
            defaults={
                'type': Exercise.MULTIPLE_CHOICE,
                'prompt': 'the man',
                'answer_text': '男人 (nánrén)',
                'is_new_word': False
            }
        )

        choices_data4 = [
            {'text': '男人 (nánrén)', 'is_correct': True},
            {'text': '女人 (nǚrén)', 'is_correct': False},
            {'text': '男孩 (nánhái)', 'is_correct': False},
        ]

        for choice_data in choices_data4:
            ExerciseChoice.objects.get_or_create(
                exercise=ex4,
                text=choice_data['text'],
                defaults={'is_correct': choice_data['is_correct']}
            )

        # Exercise 5: Simple translation with multiple words
        ex5, _ = Exercise.objects.get_or_create(
            lesson=lesson1,
            order=5,
            defaults={
                'type': Exercise.TRANSLATE,
                'prompt': '男孩和女孩 (nánhái hé nǚhái)',
                'answer_text': 'the boy and the girl',
                'hint': '和 (hé) means "and" in Chinese.'
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
                'prompt': 'How do you say "hello" in Chinese?',
                'answer_text': '你好 (nǐhǎo)',
                'is_new_word': True,
                'choices': [
                    {'text': '你好 (nǐhǎo)', 'is_correct': True},
                    {'text': '再见 (zàijiàn)', 'is_correct': False},
                    {'text': '谢谢 (xièxie)', 'is_correct': False},
                ]
            },
            {
                'order': 2,
                'type': Exercise.TRANSLATE,
                'prompt': '早上好 (zǎoshang hǎo)',
                'answer_text': 'good morning',
                'is_new_word': True,
                'hint': '早上 means morning, 好 means good'
            },
            {
                'order': 3,
                'type': Exercise.TRANSLATE,
                'prompt': 'how are you?',
                'answer_text': '你好吗？ (nǐ hǎo ma?)',
                'is_new_word': False,
            },
            {
                'order': 4,
                'type': Exercise.MULTIPLE_CHOICE,
                'prompt': 'What does 谢谢 (xièxie) mean?',
                'answer_text': 'thank you',
                'is_new_word': True,
                'choices': [
                    {'text': 'thank you', 'is_correct': True},
                    {'text': 'goodbye', 'is_correct': False},
                    {'text': 'please', 'is_correct': False},
                ]
            },
            {
                'order': 5,
                'type': Exercise.TRANSLATE,
                'prompt': '再见 (zàijiàn)',
                'answer_text': 'goodbye',
                'is_new_word': True,
                'hint': 'Used when parting ways'
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

        # Lesson 3: Numbers
        lesson3, _ = Lesson.objects.get_or_create(
            unit=unit1,
            order=3,
            defaults={
                'title': 'Numbers 1-10',
                'lesson_type': Lesson.LESSON,
                'is_locked': False
            }
        )

        # Add number exercises
        number_exercises = [
            {
                'order': 1,
                'type': Exercise.MULTIPLE_CHOICE,
                'prompt': 'What is 一 (yī)?',
                'answer_text': 'one',
                'is_new_word': True,
                'choices': [
                    {'text': 'one', 'is_correct': True},
                    {'text': 'two', 'is_correct': False},
                    {'text': 'three', 'is_correct': False},
                ]
            },
            {
                'order': 2,
                'type': Exercise.TRANSLATE,
                'prompt': '二 (èr)',
                'answer_text': 'two',
                'is_new_word': True,
            },
            {
                'order': 3,
                'type': Exercise.TRANSLATE,
                'prompt': 'three',
                'answer_text': '三 (sān)',
                'is_new_word': True,
            },
            {
                'order': 4,
                'type': Exercise.MULTIPLE_CHOICE,
                'prompt': 'How do you say "five" in Chinese?',
                'answer_text': '五 (wǔ)',
                'is_new_word': True,
                'choices': [
                    {'text': '四 (sì)', 'is_correct': False},
                    {'text': '五 (wǔ)', 'is_correct': True},
                    {'text': '六 (liù)', 'is_correct': False},
                ]
            },
            {
                'order': 5,
                'type': Exercise.TRANSLATE,
                'prompt': '十 (shí)',
                'answer_text': 'ten',
                'is_new_word': True,
            },
        ]

        for ex_data in number_exercises:
            choices_data = ex_data.pop('choices', None)
            ex, _ = Exercise.objects.get_or_create(
                lesson=lesson3,
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

        # Lesson 4: Places in the City
        lesson4, _ = Lesson.objects.get_or_create(
            unit=unit2,
            order=1,
            defaults={
                'title': 'Places in the City',
                'lesson_type': Lesson.LESSON,
                'is_locked': True
            }
        )

        # Add city vocabulary exercises
        city_exercises = [
            {
                'order': 1,
                'type': Exercise.MULTIPLE_CHOICE,
                'prompt': 'restaurant',
                'answer_text': '餐厅 (cāntīng)',
                'is_new_word': True,
                'choices': [
                    {'text': '餐厅 (cāntīng)', 'is_correct': True},
                    {'text': '商店 (shāngdiàn)', 'is_correct': False},
                    {'text': '医院 (yīyuàn)', 'is_correct': False},
                ]
            },
            {
                'order': 2,
                'type': Exercise.TRANSLATE,
                'prompt': '商店 (shāngdiàn)',
                'answer_text': 'shop',
                'is_new_word': True,
            },
            {
                'order': 3,
                'type': Exercise.TRANSLATE,
                'prompt': 'hospital',
                'answer_text': '医院 (yīyuàn)',
                'is_new_word': True,
            },
        ]

        for ex_data in city_exercises:
            choices_data = ex_data.pop('choices', None)
            ex, _ = Exercise.objects.get_or_create(
                lesson=lesson4,
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

        # Create Section 2
        section2, _ = Section.objects.get_or_create(
            course=chinese_course,
            order=2,
            defaults={
                'title': 'Build Connections',
                'description': 'Learn to communicate about family and relationships'
            }
        )

        # Create Unit 3
        unit3, _ = Unit.objects.get_or_create(
            section=section2,
            order=1,
            defaults={
                'title': 'Talk about family',
                'description': 'Learn vocabulary for family members'
            }
        )

        # Lesson 5: Family Members
        lesson5, _ = Lesson.objects.get_or_create(
            unit=unit3,
            order=1,
            defaults={
                'title': 'Family Members',
                'lesson_type': Lesson.LESSON,
                'is_locked': True
            }
        )

        # Add family vocabulary exercises
        family_exercises = [
            {
                'order': 1,
                'type': Exercise.MULTIPLE_CHOICE,
                'prompt': 'mother',
                'answer_text': '妈妈 (māma)',
                'is_new_word': True,
                'choices': [
                    {'text': '妈妈 (māma)', 'is_correct': True},
                    {'text': '爸爸 (bàba)', 'is_correct': False},
                    {'text': '姐姐 (jiějie)', 'is_correct': False},
                ]
            },
            {
                'order': 2,
                'type': Exercise.TRANSLATE,
                'prompt': '爸爸 (bàba)',
                'answer_text': 'father',
                'is_new_word': True,
            },
            {
                'order': 3,
                'type': Exercise.TRANSLATE,
                'prompt': 'older sister',
                'answer_text': '姐姐 (jiějie)',
                'is_new_word': True,
            },
        ]

        for ex_data in family_exercises:
            choices_data = ex_data.pop('choices', None)
            ex, _ = Exercise.objects.get_or_create(
                lesson=lesson5,
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

        self.stdout.write(self.style.SUCCESS('Successfully populated Chinese demo data!'))
        self.stdout.write(f'Created course: {chinese_course.title}')
        self.stdout.write(f'Created {Section.objects.filter(course=chinese_course).count()} sections')
        self.stdout.write(f'Created {Unit.objects.filter(section__course=chinese_course).count()} units')
        self.stdout.write(f'Created {Lesson.objects.filter(unit__section__course=chinese_course).count()} lessons')
        self.stdout.write(f'Created {Exercise.objects.filter(lesson__unit__section__course=chinese_course).count()} exercises')
        self.stdout.write(f'Created {DailyQuest.objects.count()} daily quests')