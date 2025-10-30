from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Count
from datetime import date, datetime, time
from .models import (
    Course, Section, Unit, Lesson, Exercise, ExerciseChoice,
    Attempt, LessonProgress, UserProfile, DailyQuest,
    UserDailyQuest, Achievement, UserAchievement
)

def restore_hearts_if_needed(profile):
    """
    Restore hearts to maximum if it's a new day since last heart restoration.
    This should be called whenever a user interacts with the app.
    """
    from datetime import datetime, time, timedelta
    
    now = datetime.now()
    
    # Check if we have a last_heart_restore field
    if profile.last_active_date:
        # Get midnight of today
        today_midnight = datetime.combine(date.today(), time.min)
        
        # Get midnight of last active date
        last_active_midnight = datetime.combine(profile.last_active_date, time.min)
        
        # If last active was before today's midnight, restore hearts
        if last_active_midnight < today_midnight:
            profile.restore_hearts()
    else:
        # First time, ensure hearts are at max
        profile.restore_hearts()

def home(request):
    # Show onboarding page for non-logged-in users
    if not request.user.is_authenticated:
        return render(request, "onboarding.html")

    # Check if user has selected a language, if not redirect to language selection
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    # Restore hearts if needed
    restore_hearts_if_needed(profile)
    
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
        restore_hearts_if_needed(profile)
        selected_language = profile.learning_language
    return render(request, "course_list.html", {"courses": courses, "selected_language": selected_language})

def course_detail(request, slug):
    course = get_object_or_404(Course, slug=slug)
    sections = course.sections.all().prefetch_related("units__lessons")

    # Update user's learning language based on course they're viewing
    if request.user.is_authenticated:
        profile = request.user.profile
        
        # Restore hearts if needed
        restore_hearts_if_needed(profile)
        
        # Map course slug to language code
        slug_to_language = {
            'spanish-to-english': 'es',
            'chinese-to-english': 'zh',
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
    profile = request.user.profile
    
    # Restore hearts if needed
    restore_hearts_if_needed(profile)
    
    # Clear any existing session data for this lesson (fresh start)
    if 'lesson_attempts' in request.session:
        if str(lesson_id) in request.session['lesson_attempts']:
            del request.session['lesson_attempts'][str(lesson_id)]
    
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

    # Restore hearts if needed
    restore_hearts_if_needed(profile)

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
    
    # Initialize session storage for tracking attempts
    if 'lesson_attempts' not in request.session:
        request.session['lesson_attempts'] = {}
    
    lesson_key = str(lesson_id)
    if lesson_key not in request.session['lesson_attempts']:
        request.session['lesson_attempts'][lesson_key] = {}
    
    exercise_key = str(exercise.id)
    
    # Get attempt count for this exercise (0 = never attempted, 1 = first attempt made, 2 = second attempt made)
    attempt_count = request.session['lesson_attempts'][lesson_key].get(exercise_key, 0)
    
    feedback = None
    show_continue = False

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
            # Simple exact match (can be improved with fuzzy matching)
            is_correct = submitted_text.lower() == exercise.answer_text.strip().lower()

        # Record the attempt in database
        Attempt.objects.create(
            user=request.user,
            exercise=exercise,
            submitted_text=submitted_text,
            selected_choice=selected_choice,
            is_correct=is_correct,
        )

        # Increment attempt count
        attempt_count += 1
        request.session['lesson_attempts'][lesson_key][exercise_key] = attempt_count
        request.session.modified = True

        if is_correct:
            # Correct answer!
            if attempt_count == 1:
                # First try - perfect!
                profile.add_xp(10)
                request.session['lesson_attempts'][lesson_key][exercise_key] = 'perfect'
            else:
                # Second try - corrected
                profile.add_xp(5)  # Half XP for retry
                request.session['lesson_attempts'][lesson_key][exercise_key] = 'corrected'
            
            request.session.modified = True
            
            # Update XP quest progress
            today = date.today()
            xp_quest = UserDailyQuest.objects.filter(
                user=request.user,
                quest__quest_type=DailyQuest.EARN_XP,
                date_assigned=today
            ).first()
            if xp_quest:
                xp_reward = 10 if attempt_count == 1 else 5
                xp_quest.update_progress(xp_reward)
            
            # Update streak
            profile.update_streak()
            
            feedback = {
                "is_correct": True,
                "correct_answer": exercise.answer_text,
                "first_try": attempt_count == 1,
                "xp_earned": 10 if attempt_count == 1 else 5
            }
            show_continue = True
        else:
            # Wrong answer
            if attempt_count == 1:
                # First attempt wrong - lose heart, allow retry
                profile.lose_heart()
                feedback = {
                    "is_correct": False,
                    "correct_answer": exercise.answer_text,
                    "allow_retry": True,
                    "first_try": True
                }
                show_continue = False
            else:
                # Second attempt also wrong - mark as failed, move on
                profile.lose_heart()
                request.session['lesson_attempts'][lesson_key][exercise_key] = 'failed'
                request.session.modified = True
                
                feedback = {
                    "is_correct": False,
                    "correct_answer": exercise.answer_text,
                    "allow_retry": False,
                    "first_try": False
                }
                show_continue = True

    return render(request, "exercise.html", {
        "lesson": lesson,
        "exercise": exercise,
        "index": index,
        "total": len(exercises),
        "feedback": feedback,
        "show_continue": show_continue,
        "attempt_count": attempt_count,
        "profile": profile,
    })

@login_required
def lesson_complete(request, lesson_id):
    lesson = get_object_or_404(Lesson, pk=lesson_id)
    exercises = list(lesson.exercises.all())
    profile = request.user.profile

    # Restore hearts if needed
    restore_hearts_if_needed(profile)

    # Get attempt tracking from session
    lesson_key = str(lesson_id)
    attempts_data = request.session.get('lesson_attempts', {}).get(lesson_key, {})
    
    # Count perfect, corrected, and failed
    perfect_count = sum(1 for v in attempts_data.values() if v == 'perfect')
    corrected_count = sum(1 for v in attempts_data.values() if v == 'corrected')
    failed_count = sum(1 for v in attempts_data.values() if v == 'failed')
    
    total_correct = perfect_count + corrected_count
    total_exercises = len(exercises)
    
    # Calculate score
    score = total_correct

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

    # Check for perfect lesson (all correct on first try)
    if perfect_count == total_exercises:
        perfect_quest = UserDailyQuest.objects.filter(
            user=request.user,
            quest__quest_type=DailyQuest.PERFECT_LESSON,
            date_assigned=today
        ).first()
        if perfect_quest:
            perfect_quest.update_progress(1)
    
    # Clear session data for this lesson
    if lesson_key in request.session.get('lesson_attempts', {}):
        del request.session['lesson_attempts'][lesson_key]
        request.session.modified = True

    return render(request, "lesson_complete.html", {
        "lesson": lesson,
        "score": score,
        "total": total_exercises,
        "perfect_count": perfect_count,
        "corrected_count": corrected_count,
        "failed_count": failed_count,
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
    
    # Restore hearts if needed
    restore_hearts_if_needed(profile)
    
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
    
    # Restore hearts if needed
    restore_hearts_if_needed(profile)
    
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

# Add these new views to your existing core/views.py file

@login_required
def leaderboards(request):
    """Display leaderboards page"""
    profile = request.user.profile
    
    # Restore hearts if needed
    restore_hearts_if_needed(profile)
    
    # Check if leaderboards are unlocked (need to complete a certain number of lessons)
    completed_lessons_count = LessonProgress.objects.filter(
        user=request.user,
        completed=True
    ).count()
    
    lessons_needed = max(0, 10 - completed_lessons_count)
    is_unlocked = completed_lessons_count >= 10
    
    return render(request, 'leaderboards.html', {
        'profile': profile,
        'is_unlocked': is_unlocked,
        'lessons_needed': lessons_needed,
        'completed_lessons_count': completed_lessons_count,
    })

@login_required
def shop(request):
    """Display shop page with purchasable items"""
    profile = request.user.profile
    
    # Restore hearts if needed
    restore_hearts_if_needed(profile)
    
    # Handle purchase requests
    if request.method == 'POST':
        item_type = request.POST.get('item_type')
        
        if item_type == 'refill_hearts':
            cost = 350
            if profile.gems >= cost:
                profile.gems -= cost
                profile.restore_hearts()
                return redirect('shop')
        elif item_type == 'streak_freeze':
            cost = 200
            if profile.gems >= cost:
                # TODO: Implement streak freeze functionality
                profile.gems -= cost
                profile.save()
                return redirect('shop')
    
    # Get or create today's daily quests for the sidebar
    today = date.today()
    daily_quests = UserDailyQuest.objects.filter(user=request.user, date_assigned=today)[:2]
    
    return render(request, 'shop.html', {
        'profile': profile,
        'daily_quests': daily_quests,
    })