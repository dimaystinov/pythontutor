from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

class UserCreationForm(forms.ModelForm):
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput)
    invitation = forms.CharField(label='Код приглашения преподавателя', max_length=100, required=False, help_text='Необязательно. По ссылке преподавателя заполняется автоматически.')
    confirm_password = forms.CharField(label='Повторите пароль', widget=forms.PasswordInput)
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')
    def clean_invitation(self):
        import uuid
        from tutorial.models import StudyGroup
        value = self.cleaned_data['invitation'].strip()
        if not value:
            return None
        try:
            code = uuid.UUID(value)
        except ValueError:
            raise ValidationError('Неверный код приглашения. Попросите ссылку у преподавателя.')
        group = StudyGroup.objects.filter(invite_code=code, registration_open=True, teacher__is_active=True, teacher__is_staff=True).first()
        if group is None:
            raise ValidationError('Приглашение недействительно или приём учеников закрыт.')
        return group

    def clean(self):
        data = super().clean()
        if data.get('password') != data.get('confirm_password'):
            self.add_error('confirm_password', 'Пароли не совпадают')
        if data.get('password'):
            candidate = User(**{k: data[k] for k in self.Meta.fields if k in data})
            try:
                password_validation.validate_password(data['password'], candidate)
            except ValidationError as e:
                self.add_error('password', e)
        return data

class UserProfileForm(forms.ModelForm):
    new_password = forms.CharField(label='Новый пароль', widget=forms.PasswordInput, required=False)
    new_password_repeated = forms.CharField(label='Повторите новый пароль', widget=forms.PasswordInput, required=False)
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')
    def clean(self):
        data = super().clean()
        password = data.get('new_password')
        if password != data.get('new_password_repeated'):
            self.add_error('new_password_repeated', 'Пароли не совпадают')
        if password:
            try:
                password_validation.validate_password(password, self.instance)
            except ValidationError as e:
                self.add_error('new_password', e)
        return data


from tutorial.models import ImageAssignment
from tutorial.image_course import catalog


class ImageAssignmentForm(forms.ModelForm):
    task_slug = forms.ChoiceField(label='Упражнение')
    due = forms.DateTimeField(label='Срок сдачи', required=False, widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}))

    class Meta:
        model = ImageAssignment
        fields = ('task_slug', 'title', 'description', 'assignee', 'due')
        labels = {'title': 'Название задания', 'description': 'Комментарий', 'assignee': 'Ученик (пусто — весь курс)'}

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['task_slug'].choices = [(task['slug'], task['title']) for task in catalog()]
        from tutorial.enrollment import teacher_students
        self.fields['assignee'].queryset = teacher_students(teacher).filter(is_active=True) if teacher else User.objects.none()
        self.fields['assignee'].label = 'Ученик (пусто — все ваши ученики)'


from tutorial.models import StudyGroup
from tutorial.enrollment import teacher_groups


class StudyGroupForm(forms.ModelForm):
    class Meta:
        model = StudyGroup
        fields = ('name', 'course', 'registration_open')


class StudentCreationForm(UserCreationForm):
    study_group = forms.ModelChoiceField(label='Учебная группа', queryset=StudyGroup.objects.none())
    invitation = None

    def __init__(self, *args, teacher, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['study_group'].queryset = teacher_groups(teacher)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True


class StudentEditForm(forms.ModelForm):
    study_group = forms.ModelChoiceField(label='Учебная группа', queryset=StudyGroup.objects.none())

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')

    def __init__(self, *args, teacher, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['study_group'].queryset = teacher_groups(teacher)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        if self.instance.pk:
            self.initial['study_group'] = self.instance.userprofile.study_group_id
