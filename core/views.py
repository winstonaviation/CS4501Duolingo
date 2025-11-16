from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Count
from datetime import date, time, timedelta
from django.http import JsonResponse
from .models import (
    Course, Section, Unit, Lesson, Exercise, ExerciseChoice,
    Attempt, LessonProgress, UserProfile, DailyQuest,
    UserDailyQuest, Achievement, UserAchievement
)
from .utils.ai_helper import generate_smart_hint, explain_mistake, check_translation_with_ai
from .utils.achievements import check_and_award_achievements, get_achievement_progress

def restore_hearts_if_needed(profile):
    """
    Restore hearts to maximum if it's a new day since last heart restoration.
    This should be called whenever a user interacts with the app.
    """
    
    
    now = timezone.now()
    
    # Check if we have a last_heart_restore field
    if profile.last_active_date:
        # Get midnight of today
        today_midnight = timezone.make_aware(timezone.datetime.combine(date.today(), time.min))
        
        # Get midnight of last active date
        last_active_midnight = timezone.make_aware(timezone.datetime.combine(profile.last_active_date, time.min))
        
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
        
        # Check if leaderboards are unlocked (need to complete a certain number of lessons)
        completed_lessons_count = LessonProgress.objects.filter(
            user=request.user,
            completed=True
        ).count()
        
        lessons_needed = max(0, 10 - completed_lessons_count)
        is_unlocked = completed_lessons_count >= 10

        return render(request, "course_detail.html", {
            "course": course,
            "sections": sections,
            "progress_map": progress_map,
            "profile": profile,
            "daily_quests": daily_quests,
            "lessons_needed": lessons_needed,
            "is_unlocked": is_unlocked,
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

    # Check if this lesson is already completed (practice mode)
    lesson_progress = LessonProgress.objects.filter(user=request.user, lesson=lesson, completed=True).first()
    is_practice_mode = lesson_progress is not None

    # In practice mode, don't check hearts
    if not is_practice_mode and profile.hearts <= 0:
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
    # Note: the value might be a string status ('perfect', 'corrected', 'failed') if already completed
    attempt_value = request.session['lesson_attempts'][lesson_key].get(exercise_key, 0)
    
    # If it's a string status (already completed), reset to 0 to allow re-doing the exercise
    if isinstance(attempt_value, str):
        attempt_count = 0
    else:
        attempt_count = int(attempt_value)
    
    feedback = None
    show_continue = False

    if request.method == "POST":
        is_correct = False
        selected_choice = None
        submitted_text = request.POST.get("answer", "").strip()
        user_choice_id = None  # Track which choice the user selected

        if exercise.type == Exercise.MULTIPLE_CHOICE:
            choice_id = request.POST.get("choice")
            if choice_id:
                selected_choice = ExerciseChoice.objects.filter(pk=choice_id, exercise=exercise).first()
                is_correct = bool(selected_choice and selected_choice.is_correct)
                user_choice_id = int(choice_id) if choice_id else None
        else:  # TRANSLATE or other text-based exercises
            # Use AI to check translation with fallback to exact match
            if exercise.type == Exercise.TRANSLATE:
                try:
                    # Try AI translation checker (Feature: Smart Translation Checking)
                    ai_result = check_translation_with_ai(
                        submitted_text,
                        exercise.answer_text,
                        exercise.prompt
                    )
                    is_correct = ai_result.get("correct", False)
                    ai_feedback = ai_result.get("feedback", "")
                except Exception as e:
                    # Fallback to exact match if AI fails
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"AI translation check failed: {e}")
                    is_correct = submitted_text.lower() == exercise.answer_text.strip().lower()
                    ai_feedback = None
            else:
                # Simple exact match for non-translation exercises
                is_correct = submitted_text.lower() == exercise.answer_text.strip().lower()
                ai_feedback = None

        # Record the attempt in database (EXISTING LOGIC - UNCHANGED)
        Attempt.objects.create(
            user=request.user,
            exercise=exercise,
            submitted_text=submitted_text,
            selected_choice=selected_choice,
            is_correct=is_correct,
        )

        # Increment attempt count (EXISTING LOGIC - UNCHANGED)
        attempt_count += 1
        request.session['lesson_attempts'][lesson_key][exercise_key] = attempt_count
        request.session.modified = True

        if is_correct:
            # Correct answer! (EXISTING LOGIC - UNCHANGED)
            if attempt_count == 1:
                # First try - perfect!
                if not is_practice_mode:  # Only award XP if not in practice mode
                    profile.add_xp(10)
                request.session['lesson_attempts'][lesson_key][exercise_key] = 'perfect'
            else:
                # Second try - corrected
                if not is_practice_mode:  # Only award XP if not in practice mode
                    profile.add_xp(5)  # Half XP for retry
                request.session['lesson_attempts'][lesson_key][exercise_key] = 'corrected'
            
            request.session.modified = True
            
            # Update XP quest progress (EXISTING LOGIC - UNCHANGED)
            if not is_practice_mode:
                today = date.today()
                xp_quest = UserDailyQuest.objects.filter(
                    user=request.user,
                    quest__quest_type=DailyQuest.EARN_XP,
                    date_assigned=today
                ).first()
                if xp_quest:
                    xp_reward = 10 if attempt_count == 1 else 5
                    xp_quest.update_progress(xp_reward)
            
            # Update streak (EXISTING LOGIC - UNCHANGED)
            profile.update_streak()
            
            # Build feedback dict (EXISTING LOGIC - ENHANCED WITH AI)
            feedback = {
                "is_correct": True,
                "correct_answer": exercise.answer_text,
                "first_try": attempt_count == 1,
                "xp_earned": 10 if attempt_count == 1 else 5,
                "user_choice_id": user_choice_id,
            }
            
            # Add AI feedback if available (NEW: AI Enhancement)
            if 'ai_feedback' in locals() and ai_feedback:
                feedback["ai_feedback"] = ai_feedback
            
            show_continue = True
        else:
            # Wrong answer (EXISTING LOGIC - UNCHANGED)
            ai_explanation = None  # Will hold AI-generated explanation
            
            if attempt_count == 1:
                # First attempt wrong - lose heart, allow retry (EXISTING LOGIC - UNCHANGED)
                if not is_practice_mode:  # Only lose hearts if not in practice mode
                    profile.lose_heart()
                
                # Generate AI explanation for the mistake (NEW: Feature #4 - AI Mistake Explanation)
                try:
                    ai_explanation = explain_mistake(
                        submitted_text,
                        exercise.answer_text,
                        exercise.prompt,
                        exercise.get_type_display()
                    )
                except Exception as e:
                    # If AI fails, continue without explanation
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"AI explanation generation failed: {e}")
                    ai_explanation = None
                
                feedback = {
                    "is_correct": False,
                    "correct_answer": exercise.answer_text,
                    "allow_retry": True,
                    "first_try": True,
                    "user_choice_id": user_choice_id,
                    "ai_explanation": ai_explanation,  # NEW: AI-generated explanation
                }
                show_continue = False
            else:
                # Second attempt also wrong - mark as failed, move on (EXISTING LOGIC - UNCHANGED)
                if not is_practice_mode:  # Only lose hearts if not in practice mode
                    profile.lose_heart()
                request.session['lesson_attempts'][lesson_key][exercise_key] = 'failed'
                request.session.modified = True
                
                # Generate explanation for the second failure too (NEW: Feature #4)
                try:
                    ai_explanation = explain_mistake(
                        submitted_text,
                        exercise.answer_text,
                        exercise.prompt,
                        exercise.get_type_display()
                    )
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"AI explanation generation failed: {e}")
                    ai_explanation = None
                
                feedback = {
                    "is_correct": False,
                    "correct_answer": exercise.answer_text,
                    "allow_retry": False,
                    "first_try": False,
                    "user_choice_id": user_choice_id,
                    "ai_explanation": ai_explanation,  # NEW: AI-generated explanation
                }
                show_continue = True

    # Render template with all data (EXISTING LOGIC - UNCHANGED)
    return render(request, "exercise.html", {
        "lesson": lesson,
        "exercise": exercise,
        "index": index,
        "total": len(exercises),
        "feedback": feedback,
        "show_continue": show_continue,
        "attempt_count": attempt_count,
        "profile": profile,
        "is_practice_mode": is_practice_mode,
    })

@login_required
def lesson_complete(request, lesson_id):
    lesson = get_object_or_404(Lesson, pk=lesson_id)
    exercises = list(lesson.exercises.all())
    profile = request.user.profile

    # Restore hearts if needed
    restore_hearts_if_needed(profile)

    # Check if this was practice mode
    lesson_progress = LessonProgress.objects.filter(user=request.user, lesson=lesson, completed=True).first()
    is_practice_mode = lesson_progress is not None

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

    # Only update progress and award XP if NOT in practice mode
    if not is_practice_mode:
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
        
        week_num = today.isocalendar()[1]
        year_num = today.year
        
        # Weekly Warrior quest (7 perfect lessons in a week)
        if perfect_count == total_exercises:
            weekly_warrior = UserDailyQuest.objects.filter(
                user=request.user,
                quest__quest_type=DailyQuest.WEEKLY_WARRIOR,
                week_assigned=week_num,
                year_assigned=year_num
            ).first()
            if weekly_warrior:
                weekly_warrior.update_progress(1)
        
        # Streak Master quest (maintain 7-day streak)
        if profile.streak_days >= 7:
            streak_master = UserDailyQuest.objects.filter(
                user=request.user,
                quest__quest_type=DailyQuest.STREAK_MASTER,
                week_assigned=week_num,
                year_assigned=year_num
            ).first()
            if streak_master and not streak_master.completed:
                streak_master.progress = profile.streak_days
                streak_master.update_progress(0)  # Just check completion

            check_and_award_achievements(request.user, achievement_type='lesson')
            check_and_award_achievements(request.user, achievement_type='xp')
            check_and_award_achievements(request.user, achievement_type='quest')
            check_and_award_achievements(request.user, achievement_type='time')
    else:
        # Practice mode - just update last_seen
        if lesson_progress:
            lesson_progress.last_seen = timezone.now()
            lesson_progress.save()
        completion_xp = 0
    
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
        "is_practice_mode": is_practice_mode,
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
    
    # Get achievement progress
    achievement_progress = get_achievement_progress(request.user)
    
    # Get recent achievements (last 6 earned)
    recent_achievements = UserAchievement.objects.filter(
        user=request.user
    ).select_related('achievement').order_by('-earned_at')[:6]
    
    # Get all achievements for display
    all_achievements = Achievement.objects.all().order_by('-xp_reward')
    
    # Create a set of earned achievement IDs for easy lookup
    earned_achievement_ids = set(
        UserAchievement.objects.filter(
            user=request.user
        ).values_list('achievement_id', flat=True)
    )
    
    return render(request, 'user_profile.html', {
        'profile': profile,
        'total_lessons_completed': total_lessons_completed,
        'recent_achievements': recent_achievements,
        'all_achievements': all_achievements,
        'earned_achievement_ids': earned_achievement_ids,
        'achievement_progress': achievement_progress,
    })

@login_required
def quests(request):
    """Display quests page with daily and weekly challenges"""
    profile = request.user.profile
    restore_hearts_if_needed(profile)
    
    today = date.today()
    
    # Get or create today's daily quests
    daily_quests = UserDailyQuest.objects.filter(
        user=request.user, 
        date_assigned=today,
        quest__is_weekly=False  # NEW: Only daily quests
    )
    
    if not daily_quests.exists():
        active_daily_quests = DailyQuest.objects.filter(is_active=True, is_weekly=False)
        for quest in active_daily_quests:
            UserDailyQuest.objects.create(
                user=request.user,
                quest=quest,
                date_assigned=today
            )
        daily_quests = UserDailyQuest.objects.filter(
            user=request.user, 
            date_assigned=today,
            quest__is_weekly=False
        )
    
    # NEW: Get or create weekly quests
    week_num = today.isocalendar()[1]
    year_num = today.year
    
    weekly_quests = UserDailyQuest.objects.filter(
        user=request.user,
        week_assigned=week_num,
        year_assigned=year_num,
        quest__is_weekly=True
    )
    
    if not weekly_quests.exists():
        active_weekly_quests = DailyQuest.objects.filter(is_active=True, is_weekly=True)
        for quest in active_weekly_quests:
            UserDailyQuest.objects.create(
                user=request.user,
                quest=quest,
                week_assigned=week_num,
                year_assigned=year_num
            )
        weekly_quests = UserDailyQuest.objects.filter(
            user=request.user,
            week_assigned=week_num,
            year_assigned=year_num,
            quest__is_weekly=True
        )
    
    # Calculate time remaining
    tomorrow = timezone.make_aware(timezone.datetime.combine(today + timedelta(days=1), time.min))
    time_remaining = tomorrow - timezone.now()
    hours_remaining = int(time_remaining.total_seconds() // 3600)
    minutes_remaining = int((time_remaining.total_seconds() % 3600) // 60)
    
    # Calculate days until end of week (Monday = start of week)
    days_until_week_end = 7 - today.weekday()
    
    return render(request, 'quests.html', {
        'profile': profile,
        'daily_quests': daily_quests,
        'weekly_quests': weekly_quests,  # NEW
        'hours_remaining': hours_remaining,
        'minutes_remaining': minutes_remaining,
        'days_until_week_end': days_until_week_end,  # NEW
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


@login_required
def get_hint_ajax(request, exercise_id):
    """
    AJAX endpoint to get AI-generated hint.
    This keeps the main page load fast.
    """
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    exercise = get_object_or_404(Exercise, pk=exercise_id)
    
    # Generate hint using AI
    hint = generate_smart_hint(exercise, request.user.profile)
    
    return JsonResponse({"hint": hint})