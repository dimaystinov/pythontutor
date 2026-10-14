# -*- coding: utf-8 -*-

from tutorial import models

from django.contrib import admin
from django import forms
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html
from django.templatetags.static import static
from tutorial.enrollment import teacher_students, teacher_groups

from django.contrib.auth.models import User

import operator


class ProblemInLessonInline(admin.TabularInline):
    model = models.ProblemInLesson
    extra = 5


class LessonInCourseInline(admin.TabularInline):
    model = models.LessonInCourse
    extra = 5


class LanguageAdmin(admin.ModelAdmin):
    pass


class ProblemAdmin(admin.ModelAdmin):
    pass


class LessonAdmin(admin.ModelAdmin):
    inlines = (ProblemInLessonInline,)


class CourseAdmin(admin.ModelAdmin):
    inlines = (LessonInCourseInline,)


def submission_sort_key(user, last_name, count):
    return last_name if count else chr(0xffff)


class NameSurnameListFilter(admin.SimpleListFilter):
    title = 'Имя, фамилия'

    parameter_name = 'name_surname'

    def lookups(self, request, model_admin):
        users = User.objects.prefetch_related().all()
        return [(user.username, '{1} {0} ({2})'.format(user.first_name, user.last_name, user.username)) for user in users]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(user__username=self.value())
        else:
            return queryset.all()


class CourseListFilter(admin.SimpleListFilter):
    title = 'Курс'

    parameter_name = 'course'

    def lookups(self, request, model_admin):
        courses = models.Course.objects.all()
        return [(course.urlname, course.title) for course in courses]

    def queryset(self, request, queryset):
        if self.value():
            queryset = queryset.exclude(user__userprofile__course=None)
            for course in models.Course.objects.all().exclude(urlname=self.value()):
                queryset = queryset.exclude(user__userprofile__course=course)
            return queryset.all()
        else:
            return queryset.all()


def make_ok(modeladmin, requst, queryset):
    queryset.update(status=1) # should be code for 'ok'!
make_ok.short_description = 'Поставить ok выбранным посылкам'


def make_accepted(modeladmin, requst, queryset):
    queryset.update(status=2) # should be code for 'accepted'!
make_accepted.short_description = 'Поставить accepted выбранным посылкам'


class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'name_surname', 'problem', 'status', 'execution_source', 'time')
    list_filter = (CourseListFilter, 'status', NameSurnameListFilter, 'problem')
    actions = [make_ok, make_accepted]

    def name_surname(self, submission):
        return '{0} {1}'.format(submission.user.first_name, submission.user.last_name)

    name_surname.short_description = 'Имя, фамилия'


class PupilAdminForm(forms.ModelForm):
    first_name = forms.CharField(label='Имя', max_length=150, required=False)
    last_name = forms.CharField(label='Фамилия', max_length=150, required=False)
    email = forms.EmailField(label='Электронная почта', required=False)

    class Meta:
        model = models.UserProfile
        fields = ('first_name', 'last_name', 'email', 'study_group', 'course')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            for name in ('first_name', 'last_name', 'email'):
                self.initial[name] = getattr(self.instance.user, name)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            for name in ('first_name', 'last_name', 'email'):
                setattr(instance.user, name, self.cleaned_data[name])
            instance.user.save(update_fields=['first_name', 'last_name', 'email'])
            instance.save()
        return instance


class UserProfileAdmin(admin.ModelAdmin):
    form = PupilAdminForm
    list_display = ('student_name', 'login', 'email', 'teacher_name', 'study_group', 'course')
    list_filter = ('course', 'study_group__teacher', 'study_group')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email')
    list_select_related = ('user', 'study_group__teacher', 'course')
    list_per_page = 30
    readonly_fields = ('login', 'teacher_name')
    fields = ('login', ('first_name', 'last_name'), 'email', 'study_group', 'teacher_name', 'course')
    change_list_template = 'admin/tutorial/userprofile/change_list.html'

    class Media:
        css = {'all': (static('css/teacher-admin.css') + '?v=2',)}

    @admin.display(description='Ученик', ordering='user__last_name')
    def student_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    @admin.display(description='Логин', ordering='user__username')
    def login(self, obj):
        return obj.user.username

    @admin.display(description='Почта')
    def email(self, obj):
        return obj.user.email

    @admin.display(description='Преподаватель')
    def teacher_name(self, obj):
        return (obj.study_group.teacher.get_full_name() or obj.study_group.teacher.username) if obj.study_group_id else 'Не назначен'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs if request.user.is_superuser else qs.filter(user__in=teacher_students(request.user))

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_staff

    def has_view_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request) and (obj is None or request.user.is_superuser or teacher_students(request.user).filter(pk=obj.user_id).exists())

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_form(self, request, obj=None, **kwargs):
        base = super().get_form(request, obj, **kwargs)
        class ScopedForm(base):
            def __init__(self, *args, **form_kwargs):
                super().__init__(*args, **form_kwargs)
                self.fields['study_group'].queryset = teacher_groups(request.user)
                if not request.user.is_superuser:
                    self.fields['study_group'].required = True
                    self.fields['course'].disabled = True
        return ScopedForm

    def save_model(self, request, obj, form, change):
        # Django's admin invokes form.save(commit=False); save related names here.
        for name in ('first_name', 'last_name', 'email'):
            setattr(obj.user, name, form.cleaned_data[name])
        obj.user.save(update_fields=['first_name', 'last_name', 'email'])
        obj.save()


class StudyGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'teacher', 'course', 'registration_open')
    list_filter = ('teacher', 'course', 'registration_open')
    search_fields = ('name', 'teacher__username', 'teacher__first_name', 'teacher__last_name')
    readonly_fields = ('invitation',)

    @admin.display(description='Ссылка регистрации (добавьте адрес вашего сайта)')
    def invitation(self, obj):
        if not obj.pk:
            return 'Сначала сохраните группу'
        path = reverse('register') + '?invite=' + str(obj.invite_code)
        return format_html('<a href="{}">{}</a>', path, path)

    def get_readonly_fields(self, request, obj=None):
        return ('invitation', 'course') if obj else ('invitation',)

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    has_add_permission = has_view_permission
    has_change_permission = has_view_permission
    has_delete_permission = has_view_permission


admin.site.register(models.StudyGroup, StudyGroupAdmin)
admin.site.site_header = 'PythonTutor — управление обучением'
admin.site.site_title = 'PythonTutor'
admin.site.index_title = 'Ученики, группы и учебные материалы'


admin.site.register(models.Language, LanguageAdmin)
admin.site.register(models.Problem, ProblemAdmin)
admin.site.register(models.Lesson, LessonAdmin)
admin.site.register(models.Course, CourseAdmin)
admin.site.register(models.Submission, SubmissionAdmin)
admin.site.register(models.UserProfile, UserProfileAdmin)
# admin.site.register(models.LessonInCourse)

admin.site.register(models.ImageSubmission)
admin.site.register(models.ImageAssignment)
