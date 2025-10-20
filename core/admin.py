from django.contrib import admin
from .models import Course, Lesson, Exercise, ExerciseChoice, Attempt, LessonProgress

class ExerciseChoiceInline(admin.TabularInline):
    model = ExerciseChoice
    extra = 1

class ExerciseAdmin(admin.ModelAdmin):
    inlines = [ExerciseChoiceInline]
    list_display = ("lesson", "order", "type", "prompt")

class LessonAdmin(admin.ModelAdmin):
    list_display = ("course", "title", "order")
    list_filter = ("course",)

admin.site.register(Course)
admin.site.register(Lesson, LessonAdmin)
admin.site.register(Exercise, ExerciseAdmin)
admin.site.register(Attempt)
admin.site.register(LessonProgress)