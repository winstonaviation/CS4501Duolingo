from django.contrib import admin
from .models import (
    Course, Section, Unit, Lesson, Exercise, ExerciseChoice,
    Attempt, LessonProgress, UserProfile, DailyQuest,
    UserDailyQuest, Achievement, UserAchievement
)

class ExerciseChoiceInline(admin.TabularInline):
    model = ExerciseChoice
    extra = 1
    fields = ("text", "is_correct", "image", "audio_file")

class ExerciseAdmin(admin.ModelAdmin):
    inlines = [ExerciseChoiceInline]
    list_display = ("lesson", "order", "type", "prompt", "is_new_word", "has_audio")  # ← Add has_audio
    list_filter = ("type", "is_new_word")
    search_fields = ("prompt", "answer_text")
    
    # Add this method
    def has_audio(self, obj):
        return bool(obj.audio_file)
    has_audio.boolean = True
    has_audio.short_description = "Audio"

class UnitInline(admin.TabularInline):
    model = Unit
    extra = 1
    fields = ("title", "order", "description")

class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    fields = ("title", "order", "lesson_type", "is_locked")

class SectionAdmin(admin.ModelAdmin):
    inlines = [UnitInline]
    list_display = ("course", "order", "title")
    list_filter = ("course",)

class UnitAdmin(admin.ModelAdmin):
    inlines = [LessonInline]
    list_display = ("section", "order", "title")
    list_filter = ("section__course",)

class LessonAdmin(admin.ModelAdmin):
    list_display = ("unit", "title", "order", "lesson_type", "is_locked")
    list_filter = ("unit__section__course", "lesson_type", "is_locked")
    search_fields = ("title",)

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "learning_language", "hearts", "gems", "xp", "streak_days", "has_selected_language")
    list_filter = ("learning_language", "has_selected_language")
    search_fields = ("user__email", "user__username")
    readonly_fields = ("created_at",)

class DailyQuestAdmin(admin.ModelAdmin):
    list_display = ("title", "quest_type", "target_value", "xp_reward", "gem_reward", "is_active")
    list_filter = ("quest_type", "is_active")

class UserDailyQuestAdmin(admin.ModelAdmin):
    list_display = ("user", "quest", "progress", "completed", "date_assigned")
    list_filter = ("completed", "date_assigned", "quest__quest_type")
    search_fields = ("user__email", "user__username")

class AchievementAdmin(admin.ModelAdmin):
    list_display = ("icon", "title", "xp_reward", "gem_reward")

class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ("user", "achievement", "earned_at")
    list_filter = ("earned_at", "achievement")
    search_fields = ("user__email", "user__username")

class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "lesson", "score", "completed", "last_seen")
    list_filter = ("completed", "lesson__unit__section__course")
    search_fields = ("user__email", "user__username")

# Register models
admin.site.register(Course)
admin.site.register(Section, SectionAdmin)
admin.site.register(Unit, UnitAdmin)
admin.site.register(Lesson, LessonAdmin)
admin.site.register(Exercise, ExerciseAdmin)
admin.site.register(Attempt)
admin.site.register(LessonProgress, LessonProgressAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(DailyQuest, DailyQuestAdmin)
admin.site.register(UserDailyQuest, UserDailyQuestAdmin)
admin.site.register(Achievement, AchievementAdmin)
admin.site.register(UserAchievement, UserAchievementAdmin)