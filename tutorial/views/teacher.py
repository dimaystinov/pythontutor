import uuid
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Count
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from tutorial.models import Course, StudyGroup, UserProfile
from tutorial.forms import StudyGroupForm, StudentCreationForm, StudentEditForm
from tutorial.enrollment import teacher_groups, teacher_students
from tutorial.views import need_admin


@need_admin
def teacher(request):
    groups = teacher_groups(request.user).annotate(student_count=Count('students'))
    students = teacher_students(request.user).select_related('userprofile__study_group__teacher', 'userprofile__course')
    query = request.GET.get('q', '').strip()
    group_id = request.GET.get('group', '')
    for term in query.split():
        students = students.filter(Q(username__icontains=term) | Q(first_name__icontains=term) | Q(last_name__icontains=term) | Q(email__icontains=term))
    if group_id:
        group = get_object_or_404(groups, pk=group_id) if group_id.isdecimal() else None
        students = students.filter(userprofile__study_group=group) if group else students.none()
    students = students.annotate(solved_count=Count('submission__problem', filter=Q(submission__status__in=[1, 2]), distinct=True)).order_by('last_name', 'first_name', 'username')
    page = Paginator(students, 30).get_page(request.GET.get('page'))
    invitations = [{'group': group, 'url': request.build_absolute_uri(reverse('register')) + '?invite=' + str(group.invite_code)} for group in groups]
    courses = Course.objects.all() if request.user.is_superuser else Course.objects.filter(studygroup__teacher=request.user).distinct()
    return render(request, 'teacher.html', {'invitations': invitations, 'groups': groups, 'page': page, 'q': query, 'selected_group': group_id, 'courses': courses.prefetch_related('lessonincourse_set__lesson')})


@need_admin
def teacher_group(request, pk=None):
    group = get_object_or_404(teacher_groups(request.user), pk=pk) if pk else None
    if request.method == 'POST' and group and request.POST.get('action') == 'rotate':
        group.invite_code = uuid.uuid4()
        group.save(update_fields=['invite_code'])
        messages.success(request, 'Создана новая ссылка. Старая больше не действует; ученики остаются в группе.')
        return redirect('teacher')
    form = StudyGroupForm(request.POST if request.method == 'POST' else None, instance=group)
    # Changing the course of an existing group would silently move all pupils.
    if group:
        form.fields['course'].disabled = True
    if request.method == 'POST' and form.is_valid():
        group = form.save(commit=False)
        if not group.pk:
            group.teacher = request.user
        group.save()
        messages.success(request, 'Группа сохранена. Ссылку для учеников можно скопировать в кабинете.')
        return redirect('teacher')
    return render(request, 'teacher_form.html', {'form': form, 'title': 'Настройки группы' if group else 'Новая учебная группа', 'group': group})


@need_admin
def teacher_student(request, pk=None):
    student = get_object_or_404(teacher_students(request.user), pk=pk) if pk else None
    kwargs = {'teacher': request.user}
    if student:
        kwargs['instance'] = student
    form = (StudentEditForm if student else StudentCreationForm)(request.POST if request.method == 'POST' else None, **kwargs)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            student = form.save(commit=False)
            if pk is None:
                student.set_password(form.cleaned_data['password'])
            student.save()
            profile = student.userprofile
            profile.study_group = form.cleaned_data['study_group']
            profile.save()
        messages.success(request, 'Ученик сохранён.')
        return redirect('teacher')
    return render(request, 'teacher_form.html', {'form': form, 'title': 'Редактировать ученика' if student else 'Добавить ученика', 'student': student, 'needs_group': not teacher_groups(request.user).exists()})


@login_required
def join_group(request, code):
    group = get_object_or_404(StudyGroup, invite_code=code, registration_open=True, teacher__is_active=True, teacher__is_staff=True)
    profile = request.user.userprofile
    if request.user.is_staff:
        return HttpResponseForbidden('Ссылка предназначена для учеников. Преподаватель управляет группами в своём кабинете.')
    conflict = profile.study_group_id and profile.study_group_id != group.pk
    if request.method == 'POST' and not conflict:
        with transaction.atomic():
            profile = UserProfile.objects.select_for_update().get(pk=profile.pk)
            if profile.study_group_id and profile.study_group_id != group.pk:
                return HttpResponseForbidden('Вы уже зачислены в другую группу.')
            profile.study_group = group
            profile.save()
        messages.success(request, 'Вы записаны в группу преподавателя.')
        return redirect('profile', request.user.username)
    return render(request, 'join_group.html', {'group': group, 'conflict': conflict})
