from django.core.management.base import BaseCommand
from core.models import Achievement


class Command(BaseCommand):
    help = 'Populate the database with sample achievements'

    def handle(self, *args, **kwargs):
        self.stdout.write('Populating achievements...')

        achievements_data = [
            # Beginner Achievements
            {
                'title': 'First Steps',
                'description': 'Complete your first lesson',
                'icon': '🎯',
                'xp_reward': 10,
                'gem_reward': 5,
            },
            {
                'title': 'Scholar',
                'description': 'Complete 5 lessons',
                'icon': '📚',
                'xp_reward': 25,
                'gem_reward': 10,
            },
            {
                'title': 'Dedicated Learner',
                'description': 'Complete 10 lessons',
                'icon': '📖',
                'xp_reward': 50,
                'gem_reward': 20,
            },
            {
                'title': 'Lesson Master',
                'description': 'Complete 25 lessons',
                'icon': '🎓',
                'xp_reward': 100,
                'gem_reward': 50,
            },
            
            # Streak Achievements
            {
                'title': 'Warming Up',
                'description': 'Reach a 3-day streak',
                'icon': '🔥',
                'xp_reward': 15,
                'gem_reward': 10,
            },
            {
                'title': 'On Fire',
                'description': 'Reach a 7-day streak',
                'icon': '🔥',
                'xp_reward': 30,
                'gem_reward': 20,
            },
            {
                'title': 'Wildfire',
                'description': 'Reach a 14-day streak',
                'icon': '🔥',
                'xp_reward': 75,
                'gem_reward': 40,
            },
            {
                'title': 'Unstoppable',
                'description': 'Reach a 30-day streak',
                'icon': '🔥',
                'xp_reward': 150,
                'gem_reward': 100,
            },
            {
                'title': 'Legendary Streak',
                'description': 'Reach a 100-day streak',
                'icon': '🔥',
                'xp_reward': 500,
                'gem_reward': 250,
            },
            
            # XP Achievements
            {
                'title': 'Rising Star',
                'description': 'Earn 100 total XP',
                'icon': '⭐',
                'xp_reward': 20,
                'gem_reward': 10,
            },
            {
                'title': 'Experience Hunter',
                'description': 'Earn 500 total XP',
                'icon': '⭐',
                'xp_reward': 50,
                'gem_reward': 25,
            },
            {
                'title': 'XP Champion',
                'description': 'Earn 1,000 total XP',
                'icon': '⭐',
                'xp_reward': 100,
                'gem_reward': 50,
            },
            {
                'title': 'XP Legend',
                'description': 'Earn 5,000 total XP',
                'icon': '⭐',
                'xp_reward': 250,
                'gem_reward': 150,
            },
            
            # Perfect Lesson Achievements
            {
                'title': 'Perfectionist',
                'description': 'Complete a perfect lesson (no mistakes)',
                'icon': '💯',
                'xp_reward': 20,
                'gem_reward': 15,
            },
            {
                'title': 'Flawless Five',
                'description': 'Complete 5 perfect lessons',
                'icon': '💯',
                'xp_reward': 50,
                'gem_reward': 30,
            },
            {
                'title': 'Perfect Ten',
                'description': 'Complete 10 perfect lessons',
                'icon': '💯',
                'xp_reward': 100,
                'gem_reward': 60,
            },
            
            # Quest Achievements
            {
                'title': 'Quest Starter',
                'description': 'Complete your first daily quest',
                'icon': '🎯',
                'xp_reward': 15,
                'gem_reward': 10,
            },
            {
                'title': 'Quest Warrior',
                'description': 'Complete 10 daily quests',
                'icon': '🎯',
                'xp_reward': 50,
                'gem_reward': 30,
            },
            {
                'title': 'Quest Master',
                'description': 'Complete 25 daily quests',
                'icon': '🎯',
                'xp_reward': 125,
                'gem_reward': 75,
            },
            
            # Special Achievements
            {
                'title': 'Early Bird',
                'description': 'Complete a lesson before 8 AM',
                'icon': '🌅',
                'xp_reward': 25,
                'gem_reward': 15,
            },
            {
                'title': 'Night Owl',
                'description': 'Complete a lesson after 10 PM',
                'icon': '🦉',
                'xp_reward': 25,
                'gem_reward': 15,
            },
            {
                'title': 'Weekend Warrior',
                'description': 'Complete lessons on Saturday and Sunday',
                'icon': '💪',
                'xp_reward': 30,
                'gem_reward': 20,
            },
            {
                'title': 'Speed Demon',
                'description': 'Complete 5 lessons in one day',
                'icon': '⚡',
                'xp_reward': 75,
                'gem_reward': 40,
            },
            {
                'title': 'Gem Collector',
                'description': 'Collect 100 gems',
                'icon': '💎',
                'xp_reward': 50,
                'gem_reward': 25,
            },
            {
                'title': 'Treasure Hunter',
                'description': 'Collect 500 gems',
                'icon': '💎',
                'xp_reward': 150,
                'gem_reward': 75,
            },
        ]

        created_count = 0
        updated_count = 0

        for achievement_data in achievements_data:
            achievement, created = Achievement.objects.update_or_create(
                title=achievement_data['title'],
                defaults={
                    'description': achievement_data['description'],
                    'icon': achievement_data['icon'],
                    'xp_reward': achievement_data['xp_reward'],
                    'gem_reward': achievement_data['gem_reward'],
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f'✓ Created: {achievement.icon} {achievement.title}'
                ))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(
                    f'↻ Updated: {achievement.icon} {achievement.title}'
                ))

        self.stdout.write(self.style.SUCCESS(f'\n{"="*60}'))
        self.stdout.write(self.style.SUCCESS('Summary'))
        self.stdout.write(self.style.SUCCESS(f'{"="*60}'))
        self.stdout.write(f'Created: {created_count}')
        self.stdout.write(f'Updated: {updated_count}')
        self.stdout.write(f'Total: {Achievement.objects.count()} achievements')