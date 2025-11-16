# core/utils/achievements.py
from django.utils import timezone
from core.models import Achievement, UserAchievement, LessonProgress, UserDailyQuest
from datetime import time


def check_and_award_achievements(user, achievement_type=None):
    """
    Check and award achievements for a user.
    
    Args:
        user: The user to check achievements for
        achievement_type: Optional specific type to check (e.g., 'lesson', 'streak', 'xp')
    
    Returns:
        List of newly earned achievements
    """
    newly_earned = []
    
    # Get user profile
    profile = user.profile
    
    # Get already earned achievements to avoid duplicates
    earned_achievement_ids = UserAchievement.objects.filter(
        user=user
    ).values_list('achievement_id', flat=True)
    
    # Check different achievement types
    if achievement_type is None or achievement_type == 'lesson':
        newly_earned.extend(check_lesson_achievements(user, profile, earned_achievement_ids))
    
    if achievement_type is None or achievement_type == 'streak':
        newly_earned.extend(check_streak_achievements(user, profile, earned_achievement_ids))
    
    if achievement_type is None or achievement_type == 'xp':
        newly_earned.extend(check_xp_achievements(user, profile, earned_achievement_ids))
    
    if achievement_type is None or achievement_type == 'perfect':
        newly_earned.extend(check_perfect_lesson_achievements(user, profile, earned_achievement_ids))
    
    if achievement_type is None or achievement_type == 'quest':
        newly_earned.extend(check_quest_achievements(user, profile, earned_achievement_ids))
    
    if achievement_type is None or achievement_type == 'time':
        newly_earned.extend(check_time_based_achievements(user, profile, earned_achievement_ids))
    
    if achievement_type is None or achievement_type == 'gems':
        newly_earned.extend(check_gem_achievements(user, profile, earned_achievement_ids))
    
    return newly_earned


def check_lesson_achievements(user, profile, earned_achievement_ids):
    """Check lesson completion achievements"""
    newly_earned = []
    
    # Count completed lessons
    completed_count = LessonProgress.objects.filter(
        user=user,
        completed=True
    ).count()
    
    # Define lesson milestones
    milestones = {
        'First Steps': 1,
        'Scholar': 5,
        'Dedicated Learner': 10,
        'Lesson Master': 25,
    }
    
    for title, required_count in milestones.items():
        if completed_count >= required_count:
            achievement = Achievement.objects.filter(title=title).first()
            if achievement and achievement.id not in earned_achievement_ids:
                user_achievement = award_achievement(user, achievement)
                if user_achievement:
                    newly_earned.append(user_achievement)
    
    return newly_earned


def check_streak_achievements(user, profile, earned_achievement_ids):
    """Check streak achievements"""
    newly_earned = []
    
    streak_days = profile.streak_days
    
    # Define streak milestones
    milestones = {
        'Warming Up': 3,
        'On Fire': 7,
        'Wildfire': 14,
        'Unstoppable': 30,
        'Legendary Streak': 100,
    }
    
    for title, required_days in milestones.items():
        if streak_days >= required_days:
            achievement = Achievement.objects.filter(title=title).first()
            if achievement and achievement.id not in earned_achievement_ids:
                user_achievement = award_achievement(user, achievement)
                if user_achievement:
                    newly_earned.append(user_achievement)
    
    return newly_earned


def check_xp_achievements(user, profile, earned_achievement_ids):
    """Check XP achievements"""
    newly_earned = []
    
    total_xp = profile.xp
    
    # Define XP milestones
    milestones = {
        'Rising Star': 100,
        'Experience Hunter': 500,
        'XP Champion': 1000,
        'XP Legend': 5000,
    }
    
    for title, required_xp in milestones.items():
        if total_xp >= required_xp:
            achievement = Achievement.objects.filter(title=title).first()
            if achievement and achievement.id not in earned_achievement_ids:
                user_achievement = award_achievement(user, achievement)
                if user_achievement:
                    newly_earned.append(user_achievement)
    
    return newly_earned


def check_perfect_lesson_achievements(user, profile, earned_achievement_ids):
    """Check perfect lesson achievements"""
    newly_earned = []
    
    # Count perfect lessons (where all exercises were correct on first try)
    # This would require tracking in session or database - for now we'll use a simpler metric
    # You could add a 'perfect_lessons' field to UserProfile to track this
    
    # For demonstration, we'll check if user has completed any lessons
    # In production, you'd want to track perfect lessons separately
    
    return newly_earned


def check_quest_achievements(user, profile, earned_achievement_ids):
    """Check quest completion achievements"""
    newly_earned = []
    
    # Count completed quests
    completed_quests = UserDailyQuest.objects.filter(
        user=user,
        completed=True
    ).count()
    
    # Define quest milestones
    milestones = {
        'Quest Starter': 1,
        'Quest Warrior': 10,
        'Quest Master': 25,
    }
    
    for title, required_count in milestones.items():
        if completed_quests >= required_count:
            achievement = Achievement.objects.filter(title=title).first()
            if achievement and achievement.id not in earned_achievement_ids:
                user_achievement = award_achievement(user, achievement)
                if user_achievement:
                    newly_earned.append(user_achievement)
    
    return newly_earned


def check_time_based_achievements(user, profile, earned_achievement_ids):
    """Check time-based achievements (early bird, night owl, etc.)"""
    newly_earned = []
    
    # Get current time
    now = timezone.now()
    current_time = now.time()
    
    # Check for Early Bird (before 8 AM)
    if current_time < time(8, 0):
        achievement = Achievement.objects.filter(title='Early Bird').first()
        if achievement and achievement.id not in earned_achievement_ids:
            user_achievement = award_achievement(user, achievement)
            if user_achievement:
                newly_earned.append(user_achievement)
    
    # Check for Night Owl (after 10 PM)
    if current_time >= time(22, 0):
        achievement = Achievement.objects.filter(title='Night Owl').first()
        if achievement and achievement.id not in earned_achievement_ids:
            user_achievement = award_achievement(user, achievement)
            if user_achievement:
                newly_earned.append(user_achievement)
    
    # Check for Weekend Warrior
    if now.weekday() in [5, 6]:  # Saturday or Sunday
        # Check if they completed lessons on both days this weekend
        # This would require more complex logic - simplified for demo
        pass
    
    return newly_earned


def check_gem_achievements(user, profile, earned_achievement_ids):
    """Check gem collection achievements"""
    newly_earned = []
    
    total_gems = profile.gems
    
    # Define gem milestones
    milestones = {
        'Gem Collector': 100,
        'Treasure Hunter': 500,
    }
    
    for title, required_gems in milestones.items():
        if total_gems >= required_gems:
            achievement = Achievement.objects.filter(title=title).first()
            if achievement and achievement.id not in earned_achievement_ids:
                user_achievement = award_achievement(user, achievement)
                if user_achievement:
                    newly_earned.append(user_achievement)
    
    return newly_earned


def award_achievement(user, achievement):
    """
    Award an achievement to a user and give them the rewards.
    
    Returns:
        UserAchievement object if newly created, None if already earned
    """
    # Check if user already has this achievement
    existing = UserAchievement.objects.filter(
        user=user,
        achievement=achievement
    ).first()
    
    if existing:
        return None
    
    # Create the user achievement
    user_achievement = UserAchievement.objects.create(
        user=user,
        achievement=achievement
    )
    
    # Award XP and gems
    profile = user.profile
    profile.add_xp(achievement.xp_reward)
    profile.add_gems(achievement.gem_reward)
    
    return user_achievement


def get_achievement_progress(user):
    """
    Get progress towards all achievements.
    
    Returns:
        Dict with achievement categories and progress
    """
    profile = user.profile
    
    # Completed lessons
    completed_lessons = LessonProgress.objects.filter(
        user=user,
        completed=True
    ).count()
    
    # Completed quests
    completed_quests = UserDailyQuest.objects.filter(
        user=user,
        completed=True
    ).count()
    
    # Earned achievements
    earned_count = UserAchievement.objects.filter(user=user).count()
    total_count = Achievement.objects.count()
    
    return {
        'earned_achievements': earned_count,
        'total_achievements': total_count,
        'percentage': int((earned_count / total_count * 100)) if total_count > 0 else 0,
        'stats': {
            'completed_lessons': completed_lessons,
            'streak_days': profile.streak_days,
            'total_xp': profile.xp,
            'total_gems': profile.gems,
            'completed_quests': completed_quests,
        }
    }