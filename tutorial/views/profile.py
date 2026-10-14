from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from tutorial.forms import UserCreationForm, UserProfileForm
from tutorial.models import Submission
from tutorial.enrollment import teacher_students
from django.contrib import messages

@login_required
def profile(request, username):
    user = get_object_or_404(User, username=username)
    if request.user != user and not (request.user.is_staff and teacher_students(request.user).filter(pk=user.pk).exists()):
        return HttpResponseForbidden('Доступ разрешён владельцу профиля и преподавателю.')
    editable = request.user == user
    if request.method == 'POST' and not editable:
        return HttpResponseForbidden()
    form = UserProfileForm(request.POST if request.method == 'POST' else None, instance=user)
    changed = False
    if request.method == 'POST' and form.is_valid():
        user = form.save(commit=False)
        if form.cleaned_data['new_password']:
            user.set_password(form.cleaned_data['new_password'])
        user.save()
        update_session_auth_hash(request, user)
        changed = True
    submissions = Submission.objects.filter(user=user).select_related('problem').order_by('-time')
    return render(request, 'profile.html', locals())

def register_user(request):
    invite = request.POST.get('invitation', '') if request.method == 'POST' else request.GET.get('invite', '')
    form = UserCreationForm(request.POST if request.method == 'POST' else None, initial={'invitation': invite})
    invitation_group = None
    if invite:
        import uuid
        from tutorial.models import StudyGroup
        try:
            invitation_group = StudyGroup.objects.filter(invite_code=uuid.UUID(invite), registration_open=True, teacher__is_active=True, teacher__is_staff=True).select_related('teacher', 'course').first()
        except ValueError:
            pass
    if request.user.is_authenticated:
        if invitation_group:
            return redirect('join_group', code=invitation_group.invite_code)
        return redirect('profile', request.user.username)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            if form.cleaned_data['invitation']:
                enrollment = user.userprofile
                enrollment.study_group = form.cleaned_data['invitation']
                enrollment.save()
        messages.success(request, 'Регистрация завершена. Войдите с выбранными логином и паролем.')
        return redirect('login')
    return render(request, 'register.html', {'form': form, 'invitation_group': invitation_group, 'invalid_invitation': bool(invite and not invitation_group)})
