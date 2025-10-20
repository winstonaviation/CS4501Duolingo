from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Count
from .models import Course, Lesson, Exercise, ExerciseChoice, Attempt, LessonProgress

def home(request):
    top_courses = Course.objects.annotate(n_lessons=Count("lessons")).order_by("-n_lessons")[:6]
    return render(request, "home.html", {"courses": top_courses})

def course_list(request):
    courses = Course.objects.all()
    return render(request, "course_list.html", {"courses": courses})

def course_detail(request, slug):
    course = get_object_or_404(Course, slug=slug)
    lessons = course.lessons.all().order_by("order")
    # attach progress if logged in
    progress_map = {}
    if request.user.is_authenticated:
        progress_map = {lp.lesson_id: lp for lp in LessonProgress.objects.filter(user=request.user, lesson__course=course)}
    return render(request, "course_detail.html", {"course": course, "lessons": lessons, "progress_map": progress_map})

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
    })

@login_required
def lesson_complete(request, lesson_id):
    lesson = get_object_or_404(Lesson, pk=lesson_id)
    exercises = list(lesson.exercises.all())
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

    return render(request, "lesson_complete.html", {"lesson": lesson, "score": score, "total": len(exercises)})
