# -*- coding: utf-8 -*-

import uuid
from django.db import models
from django.contrib.auth.models import User


# currently totally unused model
class Language(models.Model):
    name = models.CharField('Внутреннее название языка', max_length=200, unique=True)

    def __str__(self):
        return self.name


class Problem(models.Model):
    urlname = models.CharField('Имя для адресной строки', max_length=200, unique=True, db_index=True)
    filename = models.CharField('Имя файла с задачей', max_length=200, blank=True)

    def __str__(self):
        return '{self.urlname}'.format(**locals())


class Lesson(models.Model):
    title = models.CharField('Название', max_length=200)
    description = models.TextField('Описание', blank=True)
    # Currently description is nowhere viewed
    urlname = models.CharField('Имя для адресной строки', max_length=200, unique=True, db_index=True)
    filename = models.CharField('Имя файла с уроком', max_length=200, blank=True)
    problems = models.ManyToManyField(Problem, through='ProblemInLesson', blank=True)
    external_contest_link = models.CharField('Внешняя ссылка на контест', max_length=200, blank=True)

    def __str__(self):
        return '{self.urlname}: {self.title} (файл: {self.filename})'.format(**locals())

    def __le__(self, other):
        return self.id < other.id


class ProblemInLesson(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    order = models.IntegerField()

    class Meta:
        ordering = ['order', 'id']
        constraints = [models.UniqueConstraint(fields=['problem', 'lesson'], name='unique_problem_lesson')]


class Course(models.Model):
    OK_AC_POLICY_CHOICES = (
        (0, 'just_ok'),
        (1, 'use_accepted_instead_of_ok'),
    )

    title = models.CharField('Название', max_length=200)
    description = models.TextField('Описание', blank=True)
    urlname = models.CharField('Имя для адресной строки', max_length=200, unique=True, db_index=True)
    lessons = models.ManyToManyField(Lesson, through='LessonInCourse', blank=True)
    language = models.ForeignKey(Language, blank=True, null=True, on_delete=models.SET_NULL)  # unused field
    ok_ac_policy = models.IntegerField(choices=OK_AC_POLICY_CHOICES, default=0)

    def __str__(self):
        return self.title


class LessonInCourse(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    order = models.IntegerField()

    class Meta:
        ordering = ['order', 'id']
        constraints = [models.UniqueConstraint(fields=['lesson', 'course'], name='unique_lesson_course')]


class StudyGroup(models.Model):
    name = models.CharField('Группа / класс', max_length=100)
    teacher = models.ForeignKey(User, on_delete=models.PROTECT, related_name='teaching_groups', verbose_name='Преподаватель', limit_choices_to={'is_staff': True, 'is_active': True})
    course = models.ForeignKey(Course, on_delete=models.PROTECT, verbose_name='Курс')
    invite_code = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    registration_open = models.BooleanField('Приём учеников открыт', default=True)

    class Meta:
        verbose_name = 'Учебная группа'
        verbose_name_plural = 'Учебные группы'
        ordering = ['name', 'pk']

    def __str__(self):
        return f'{self.name} — {self.teacher.get_full_name() or self.teacher.username}'


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    # hidden = models.BooleanField(default=True)
    course = models.ForeignKey(Course, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='Курс')
    study_group = models.ForeignKey(StudyGroup, null=True, blank=True, on_delete=models.SET_NULL, related_name='students', verbose_name='Учебная группа', help_text='Преподаватель и курс определяются выбранной группой.')

    class Meta:
        verbose_name = 'Ученик / профиль'
        verbose_name_plural = 'Ученики и профили'

    def save(self, *args, **kwargs):
        if self.study_group_id:
            self.course_id = self.study_group.course_id
            if kwargs.get('update_fields') is not None:
                kwargs['update_fields'] = set(kwargs['update_fields']) | {'course'}
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.user.get_full_name() or self.user.username} ({self.user.username})'


    def __unicode__(self):
        return '{0} {1} ({2})'.format(self.user.first_name, self.user.last_name, self.user.username)


class Submission(models.Model):
    STATUS_CHOICES = (
        (0, 'error'), # don't remove this value, or you will have a mess in your database!
        (1, 'ok'),
        (2, 'accepted'),
        (3, 'coding_style_violation'),
        (4, 'ignored'),
    )

    execution_source = models.CharField(max_length=10, default='server', choices=[('server', 'Сервер'), ('browser', 'Браузер ученика')])
    code = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    problem = models.ForeignKey(Problem, db_index=True, on_delete=models.CASCADE)
    status = models.IntegerField(choices=STATUS_CHOICES)
    time = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True)

    def __str__(self):
        return '{self.user.first_name} {self.user.last_name} on {self.problem}: {0} ({self.time})'\
                .format(self.get_status_display(), **locals())


class RequestQuota(models.Model):
    """Shared fixed-window limits for authentication and runner requests."""
    key = models.CharField(max_length=100, primary_key=True)
    window = models.BigIntegerField()
    count = models.PositiveIntegerField(default=0)


class ImageSubmission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    task_slug = models.SlugField(max_length=100, db_index=True)
    execution_source = models.CharField(max_length=10, default='server', choices=[('server', 'Сервер'), ('browser', 'Браузер ученика')])
    code = models.TextField()
    status = models.CharField(max_length=10, choices=[('ok', 'Решено'), ('error', 'Ошибка')])
    time = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-time']


class ImageAssignment(models.Model):
    task_slug = models.SlugField(max_length=100)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    assignee = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name='image_assignments')
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_image_assignments')
    due = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class TutorChatTurn(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    kind = models.CharField(max_length=12)
    slug = models.SlugField(max_length=200)
    request_id = models.UUIDField()
    question = models.TextField()
    answer = models.TextField(blank=True)
    state = models.CharField(max_length=10, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'pk']
        constraints = [models.UniqueConstraint(fields=['user', 'request_id'], name='unique_tutor_chat_request')]
        indexes = [models.Index(fields=['user', 'kind', 'slug'])]
