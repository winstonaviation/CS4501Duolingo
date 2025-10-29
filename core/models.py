from django.conf import settings
from django.db import models
from django.utils import timezone

User = settings.AUTH_USER_MODEL

class Course(models.Model):
    title = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    from_language = models.CharField(max_length=50, default="Chinese")
    to_language = models.CharField(max_length=50, default="English")
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.title} ({self.from_language}→{self.to_language})"

class Section(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="sections")
    title = models.CharField(max_length=120)
    order = models.PositiveIntegerField(default=1)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["course", "order"]
        unique_together = [("course", "order")]

    def __str__(self):
        return f"{self.course.title} - Section {self.order}: {self.title}"

class Unit(models.Model):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="units")
    title = models.CharField(max_length=120)
    order = models.PositiveIntegerField(default=1)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["section", "order"]
        unique_together = [("section", "order")]

    def __str__(self):
        return f"Section {self.section.order}, Unit {self.order}: {self.title}"

class Lesson(models.Model):
    LESSON = "lesson"
    PRACTICE = "practice"
    STORY = "story"
    UNIT_REVIEW = "unit_review"

    TYPE_CHOICES = [
        (LESSON, "Lesson"),
        (PRACTICE, "Practice"),
        (STORY, "Story"),
        (UNIT_REVIEW, "Unit Review"),
    ]

    # Temporarily nullable to allow migration of existing data
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="lessons", null=True, blank=True)
    # Keep legacy course field for backward compatibility during migration
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="legacy_lessons", null=True, blank=True)
    title = models.CharField(max_length=120)
    order = models.PositiveIntegerField(default=1)
    lesson_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=LESSON)
    is_locked = models.BooleanField(default=False)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        if self.unit:
            return f"{self.unit}: {self.title}"
        return f"{self.title}"

class Exercise(models.Model):
    MULTIPLE_CHOICE = "MC"
    TRANSLATE = "TR"
    MATCH_PAIRS = "MP"
    LISTEN = "LS"
    SPEAK = "SP"

    TYPE_CHOICES = [
        (MULTIPLE_CHOICE, "Multiple Choice"),
        (TRANSLATE, "Translate"),
        (MATCH_PAIRS, "Match Pairs"),
        (LISTEN, "Listen"),
        (SPEAK, "Speak"),
    ]

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="exercises")
    order = models.PositiveIntegerField(default=1)
    type = models.CharField(max_length=2, choices=TYPE_CHOICES, default=TRANSLATE)

    # prompt shown to learner (e.g., a Chinese sentence or "Which one of these is 'the boy'?")
    prompt = models.CharField(max_length=255)
    # canonical correct answer (for TR) or explanation
    answer_text = models.CharField(max_length=255, blank=True)

    # Optional audio file for listening exercises
    audio_file = models.FileField(upload_to="exercise_audio/", blank=True, null=True)

    # Flag to show "NEW WORD" badge
    is_new_word = models.BooleanField(default=False)

    # Optional hint or explanation text
    hint = models.TextField(blank=True)

    class Meta:
        ordering = ["lesson", "order"]
        unique_together = [("lesson", "order")]

    def __str__(self):
        return f"{self.lesson} | {self.get_type_display()} #{self.order}"

class ExerciseChoice(models.Model):
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    # Optional image for visual multiple choice (like the character images)
    image = models.ImageField(upload_to="exercise_choices/", blank=True, null=True)

    # Optional audio for listening choices
    audio_file = models.FileField(upload_to="choice_audio/", blank=True, null=True)

    def __str__(self):
        return f"[{'✓' if self.is_correct else ' '}] {self.text}"

class Attempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    submitted_text = models.CharField(max_length=255, blank=True)
    selected_choice = models.ForeignKey(ExerciseChoice, null=True, blank=True, on_delete=models.SET_NULL)
    is_correct = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

class LessonProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    score = models.IntegerField(default=0)  # simple score (e.g., # correct)
    last_seen = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("user", "lesson")]

class UserProfile(models.Model):
    SPANISH = "es"
    CHINESE = "zh"
    FRENCH = "fr"
    LANGUAGE_CHOICES = [
        (SPANISH, "Spanish"),
        (CHINESE, "Chinese"),
        (FRENCH, "French"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    learning_language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, null=True, blank=True)
    has_selected_language = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    # Gamification fields
    hearts = models.IntegerField(default=5)
    max_hearts = models.IntegerField(default=5)
    gems = models.IntegerField(default=0)
    xp = models.IntegerField(default=0)
    streak_days = models.IntegerField(default=0)
    last_active_date = models.DateField(null=True, blank=True)
    last_heart_restore = models.DateTimeField(null=True, blank=True, help_text="Last time hearts were restored to maximum")

    def __str__(self):
        return f"{self.user} - Learning: {self.get_learning_language_display() if self.learning_language else 'Not selected'}"

    def lose_heart(self):
        """Deduct one heart, minimum 0"""
        if self.hearts > 0:
            self.hearts -= 1
            self.save()

    def restore_hearts(self):
        """Restore hearts to maximum and update restore timestamp"""
        from datetime import datetime
        self.hearts = self.max_hearts
        self.last_heart_restore = datetime.now()
        self.save()

    def add_xp(self, amount):
        """Add XP to the user's profile"""
        self.xp += amount
        self.save()

    def add_gems(self, amount):
        """Add gems to the user's profile"""
        self.gems += amount
        self.save()

    def update_streak(self):
        """Update streak based on last active date"""
        from datetime import date, timedelta

        today = date.today()

        if self.last_active_date is None:
            # First time activity
            self.streak_days = 1
            self.last_active_date = today
        elif self.last_active_date == today:
            # Already active today, no change
            pass
        elif self.last_active_date == today - timedelta(days=1):
            # Active yesterday, increment streak
            self.streak_days += 1
            self.last_active_date = today
        else:
            # Streak broken, reset to 1
            self.streak_days = 1
            self.last_active_date = today

        self.save()

class DailyQuest(models.Model):
    EARN_XP = "earn_xp"
    COMPLETE_LESSONS = "complete_lessons"
    PERFECT_LESSON = "perfect_lesson"
    USE_NO_HEARTS = "use_no_hearts"

    QUEST_TYPE_CHOICES = [
        (EARN_XP, "Earn XP"),
        (COMPLETE_LESSONS, "Complete Lessons"),
        (PERFECT_LESSON, "Get a Perfect Lesson"),
        (USE_NO_HEARTS, "Complete without losing hearts"),
    ]

    quest_type = models.CharField(max_length=20, choices=QUEST_TYPE_CHOICES)
    title = models.CharField(max_length=120)
    description = models.TextField()
    target_value = models.IntegerField(default=10)
    xp_reward = models.IntegerField(default=10)
    gem_reward = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.title} (Target: {self.target_value})"

class UserDailyQuest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="daily_quests")
    quest = models.ForeignKey(DailyQuest, on_delete=models.CASCADE)
    progress = models.IntegerField(default=0)
    completed = models.BooleanField(default=False)
    date_assigned = models.DateField(default=timezone.now)

    class Meta:
        unique_together = [("user", "quest", "date_assigned")]

    def __str__(self):
        return f"{self.user} - {self.quest.title}: {self.progress}/{self.quest.target_value}"

    def update_progress(self, increment=1):
        """Update quest progress and mark as completed if target reached"""
        self.progress += increment
        if self.progress >= self.quest.target_value:
            self.completed = True
        self.save()

class Achievement(models.Model):
    title = models.CharField(max_length=120)
    description = models.TextField()
    icon = models.CharField(max_length=50, default="🏆")
    xp_reward = models.IntegerField(default=50)
    gem_reward = models.IntegerField(default=10)

    def __str__(self):
        return f"{self.icon} {self.title}"

class UserAchievement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="achievements")
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("user", "achievement")]

    def __str__(self):
        return f"{self.user} - {self.achievement.title}"