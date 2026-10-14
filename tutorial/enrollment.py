"""One ownership rule for teacher pages, reports and assignment recipients."""
from django.contrib.auth.models import User
from tutorial.models import StudyGroup


def teacher_groups(user):
    groups = StudyGroup.objects.select_related('teacher', 'course')
    return groups if user.is_superuser else groups.filter(teacher=user)


def teacher_students(user):
    users = User.objects.filter(is_staff=False, is_superuser=False)
    return users if user.is_superuser else users.filter(userprofile__study_group__teacher=user)
