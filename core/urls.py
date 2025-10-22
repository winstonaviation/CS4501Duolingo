from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("select-language/", views.language_selection, name="language_selection"),
    path("courses/", views.course_list, name="course_list"),
    path("courses/<slug:slug>/", views.course_detail, name="course_detail"),
    path("lessons/<int:lesson_id>/start/", views.lesson_start, name="lesson_start"),
    path("lessons/<int:lesson_id>/exercise/<int:index>/", views.exercise_play, name="exercise_play"),
    path("lessons/<int:lesson_id>/complete/", views.lesson_complete, name="lesson_complete"),
    path("profile/", views.user_profile, name="user_profile"),
]