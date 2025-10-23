from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Count
from datetime import date
from .models import (
    Course, Section, Unit, Lesson, Exercise, ExerciseChoice,
    Attempt, LessonProgress, UserProfile, DailyQuest,
    UserDailyQuest, Achievement, UserAchievement
)

def home(request):
    # Show onboarding page for non-logged-in users
    if not request.user.is_authenticated:
        return render(request, "onboarding.html")

    # Check if user has selected a language, if not redirect to language selection
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if not profile.has_selected_language:
        return redirect("language_selection")

    # Redirect to the course detail page for their learning language
    if profile.learning_language:
        # Map learning language to course slug
        language_map = {
            'es': 'spanish-to-english',
            'zh': 'chinese-to-english',
            'fr': 'french-to-english',
        }
        course_slug = language_map.get(profile.learning_language)
        if course_slug:
            return redirect("course_detail", slug=course_slug)
    
    # Fallback: show courses list
    top_courses = Course.objects.annotate(n_lessons=Count("sections__units__lessons")).order_by("-n_lessons")[:6]
    return render(request, "home.html", {"courses": top_courses})

def course_list(request):
    courses = Course.objects.all()
    selected_language = None
    if request.user.is_authenticated:
        profile = request.user.profile
        selected_language = profile.learning_language
    return render(request, "course_list.html", {"courses": courses, "selected_language": selected_language})

def course_detail(request, slug):
    course = get_object_or_404(Course, slug=slug)
    sections = course.sections.all().prefetch_related("units__lessons")

    # Update user's learning language based on course they're viewing
    if request.user.is_authenticated:
        profile = request.user.profile
        
        # Map course slug to language code
        slug_to_language = {
            'spanish-to-english': 'es',
            'zh-en-basics': 'zh',
            'french-to-english': 'fr',
        }
        
        course_language = slug_to_language.get(slug)
        if course_language and profile.learning_language != course_language:
            profile.learning_language = course_language
            profile.has_selected_language = True
            profile.save()

        # Get progress map
        all_lessons = Lesson.objects.filter(unit__section__course=course)
        progress_map = {lp.lesson_id: lp for lp in LessonProgress.objects.filter(user=request.user, lesson__in=all_lessons)}

        # Get or create daily quests for today
        today = date.today()
        daily_quests = UserDailyQuest.objects.filter(user=request.user, date_assigned=today)
        
        # If no quests exist for today, create them
        if not daily_quests.exists():
            active_quests = DailyQuest.objects.filter(is_active=True)
            for quest in active_quests:
                UserDailyQuest.objects.create(
                    user=request.user,
                    quest=quest,
                    date_assigned=today
                )
            daily_quests = UserDailyQuest.objects.filter(user=request.user, date_assigned=today)

        return render(request, "course_detail.html", {
            "course": course,
            "sections": sections,
            "progress_map": progress_map,
            "profile": profile,
            "daily_quests": daily_quests,
        })

    return render(request, "course_detail.html", {"course": course, "sections": sections, "progress_map": {}})

@login_required
def lesson_start(request, lesson_id):
    lesson = get_object_or_404(Lesson, pk=lesson_id)
    exercises = list(lesson.exercises.all().order_by("order"))
    if not exercises:
        return render(request, "lesson_empty.html", {"lesson": lesson})
    # start at first exercise index = 1
    return redirect("exercise_play", lesson_id=lesson.id, index=1)

@login_required
def exercise_play(request, lesson_id, index: int):
    lesson = get_object_or_404(Lesson, pk=lesson_id)
    exercises = list(lesson.exercises.all().order_by("order"))
    profile = request.user.profile

    # Check if user has hearts
    if profile.hearts <= 0:
        return render(request, "no_hearts.html", {"profile": profile})

    if not exercises:
        return redirect("lesson_complete", lesson_id=lesson.id)
    # clamp index
    if index < 1: index = 1
    if index > len(exercises):  # finished
        return redirect("lesson_complete", lesson_id=lesson.id)

    exercise = exercises[index-1]
    feedback = None

    if request.method == "POST":
        is_correct = False
        selected_choice = None
        submitted_text = request.POST.get("answer", "").strip()

        if exercise.type == Exercise.MULTIPLE_CHOICE:
            choice_id = request.POST.get("choice")
            if choice_id:
                selected_choice = ExerciseChoice.objects.filter(pk=choice_id, exercise=exercise).first()
                is_correct = bool(selected_choice and selected_choice.is_correct)
        else:  # TRANSLATE
            # super simple exact match; you can later add normalization and fuzzy match
            is_correct = submitted_text.lower() == exercise.answer_text.strip().lower()

        Attempt.objects.create(
            user=request.user,
            exercise=exercise,
            submitted_text=submitted_text,
            selected_choice=selected_choice,
            is_correct=is_correct,
        )

        # Update hearts and XP
        if not is_correct:
            profile.lose_heart()
        else:
            profile.add_xp(10)  # Award 10 XP for correct answer
            
            # Update XP quest progress
            today = date.today()
            xp_quest = UserDailyQuest.objects.filter(
                user=request.user,
                quest__quest_type=DailyQuest.EARN_XP,
                date_assigned=today
            ).first()
            if xp_quest:
                xp_quest.update_progress(10)

        # Update streak
        profile.update_streak()

        # Small inline feedback
        feedback = {
            "is_correct": is_correct,
            "correct_answer": exercise.answer_text,
        }
        # If correct, advance automatically; else stay on the same one with feedback
        if is_correct:
            return redirect("exercise_play", lesson_id=lesson.id, index=index+1)

    return render(request, "exercise.html", {
        "lesson": lesson,
        "exercise": exercise,
        "index": index,
        "total": len(exercises),
        "feedback": feedback,
        "profile": profile,
    })

@login_required
def lesson_complete(request, lesson_id):
    lesson = get_object_or_404(Lesson, pk=lesson_id)
    exercises = list(lesson.exercises.all())
    profile = request.user.profile

    # compute score = correct attempts on these exercises (latest per exercise)
    latest = (
        Attempt.objects
        .filter(user=request.user, exercise__in=exercises)
        .order_by("exercise_id", "-created_at")
    )
    latest_by_ex = {}
    for a in latest:
        if a.exercise_id not in latest_by_ex:
            latest_by_ex[a.exercise_id] = a
    score = sum(1 for a in latest_by_ex.values() if a.is_correct)

    lp, _ = LessonProgress.objects.get_or_create(user=request.user, lesson=lesson)
    lp.score = score
    lp.completed = True
    lp.last_seen = timezone.now()
    lp.save()

    # Award completion bonus XP
    completion_xp = 20
    profile.add_xp(completion_xp)

    # Update daily quest progress
    today = date.today()
    
    # Update XP quest
    xp_quest = UserDailyQuest.objects.filter(
        user=request.user,
        quest__quest_type=DailyQuest.EARN_XP,
        date_assigned=today
    ).first()
    if xp_quest:
        xp_quest.update_progress(completion_xp)
    
    # Update lessons quest
    lesson_quest = UserDailyQuest.objects.filter(
        user=request.user,
        quest__quest_type=DailyQuest.COMPLETE_LESSONS,
        date_assigned=today
    ).first()
    if lesson_quest:
        lesson_quest.update_progress(1)

    # Check for perfect lesson (all correct)
    if score == len(exercises):
        perfect_quest = UserDailyQuest.objects.filter(
            user=request.user,
            quest__quest_type=DailyQuest.PERFECT_LESSON,
            date_assigned=today
        ).first()
        if perfect_quest:
            perfect_quest.update_progress(1)

    return render(request, "lesson_complete.html", {
        "lesson": lesson,
        "score": score,
        "total": len(exercises),
        "profile": profile,
        "completion_xp": completion_xp,
    })

@login_required
def language_selection(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    # If user has already selected a language, redirect to home
    if profile.has_selected_language:
        return redirect("home")

    if request.method == "POST":
        language = request.POST.get("language")
        if language in dict(UserProfile.LANGUAGE_CHOICES):
            profile.learning_language = language
            profile.has_selected_language = True
            profile.save()
            return redirect("home")

    languages = [
        {"code": UserProfile.SPANISH, "name": "Spanish", "flag": "🇪🇸", "native_name": "Español"},
        {"code": UserProfile.FRENCH, "name": "French", "flag": "🇫🇷", "native_name": "Français"},
        {"code": UserProfile.CHINESE, "name": "Chinese", "flag": "🇨🇳", "native_name": "中文"},
    ]

    return render(request, "language_selection.html", {"languages": languages})

@login_required
def user_profile(request):
    """Display user profile page"""
    profile = request.user.profile
    
    # Get user statistics
    total_lessons_completed = LessonProgress.objects.filter(
        user=request.user,
        completed=True
    ).count()
    
    # Get recent achievements
    recent_achievements = UserAchievement.objects.filter(
        user=request.user
    ).select_related('achievement').order_by('-earned_at')[:6]
    
    return render(request, 'user_profile.html', {
        'profile': profile,
        'total_lessons_completed': total_lessons_completed,
        'recent_achievements': recent_achievements,
    })

@login_required
def quests(request):
    """Display quests page with daily and weekly challenges"""
    profile = request.user.profile
    today = date.today()
    
    # Get or create today's daily quests
    daily_quests = UserDailyQuest.objects.filter(user=request.user, date_assigned=today)
    
    # If no quests exist for today, create them
    if not daily_quests.exists():
        active_quests = DailyQuest.objects.filter(is_active=True)
        for quest in active_quests:
            UserDailyQuest.objects.create(
                user=request.user,
                quest=quest,
                date_assigned=today
            )
        daily_quests = UserDailyQuest.objects.filter(user=request.user, date_assigned=today)
    
    # Calculate time remaining until quests refresh
    from datetime import datetime, timedelta
    tomorrow = datetime.combine(today + timedelta(days=1), datetime.min.time())
    time_remaining = tomorrow - datetime.now()
    hours_remaining = int(time_remaining.total_seconds() // 3600)
    minutes_remaining = int((time_remaining.total_seconds() % 3600) // 60)
    
    return render(request, 'quests.html', {
        'profile': profile,
        'daily_quests': daily_quests,
        'hours_remaining': hours_remaining,
        'minutes_remaining': minutes_remaining,
    })