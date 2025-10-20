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

class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=120)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["course", "order"]
        unique_together = [("course", "order")]

    def __str__(self):
        return f"{self.course.title}: {self.title}"

class Exercise(models.Model):
    MULTIPLE_CHOICE = "MC"
    TRANSLATE = "TR"
    TYPE_CHOICES = [
        (MULTIPLE_CHOICE, "Multiple Choice"),
        (TRANSLATE, "Translate"),
    ]

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="exercises")
    order = models.PositiveIntegerField(default=1)
    type = models.CharField(max_length=2, choices=TYPE_CHOICES, default=TRANSLATE)

    # prompt shown to learner (e.g., a Chinese sentence)
    prompt = models.CharField(max_length=255)
    # canonical correct answer (for TR) or explanation
    answer_text = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["lesson", "order"]
        unique_together = [("lesson", "order")]

    def __str__(self):
        return f"{self.lesson} | {self.get_type_display()} #{self.order}"

class ExerciseChoice(models.Model):
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

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
