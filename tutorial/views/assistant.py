import base64
import uuid
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from tutorial.ai_tutor import context_for, configured, build_messages, generate, TutorUnavailable
from tutorial.models import TutorChatTurn
from tutorial.image_course import canonical_image, MAX_BYTES
from tutorial.speech import available as voice_available


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def assistant_chat(request, kind, slug):
    context = context_for(request.user, kind, slug)
    turns = TutorChatTurn.objects.filter(user=request.user, kind=kind, slug=slug, state='done')
    if request.method == 'GET':
        recent = list(turns.order_by('-created_at', '-pk')[:30])[::-1]
        return JsonResponse({'title':context['title'], 'solved':context['solved'], 'configured':configured(), 'voice_available':voice_available(), 'turns':[{'id':str(t.request_id), 'question':t.question, 'answer':t.answer} for t in recent]})
    question = request.POST.get('question', '').strip()
    code = request.POST.get('code', '')
    if not question or len(question) > 3000 or len(code) > 12000:
        return JsonResponse({'error':'Вопрос — от 1 до 3000 символов, код — до 12000 символов.'}, status=400)
    try:
        request_id = uuid.UUID(request.POST.get('request_id', ''))
    except ValueError:
        return JsonResponse({'error':'Обновите страницу и повторите вопрос.'}, status=400)
    existing = TutorChatTurn.objects.filter(user=request.user, request_id=request_id).first()
    if existing:
        if existing.kind != kind or existing.slug != slug:
            return JsonResponse({'error':'Этот запрос относится к другой задаче.'}, status=409)
        if existing.state == 'done':
            return JsonResponse({'answer':existing.answer, 'question':existing.question, 'id':str(request_id)})
        return JsonResponse({'error':'Запрос уже отправлен. Обновите историю или отправьте новый вопрос.'}, status=409)
    if not configured():
        return JsonResponse({'error':'ИИ-помощник ещё не подключён администратором.'}, status=503)
    today = timezone.now() - timedelta(days=1)
    if TutorChatTurn.objects.filter(user=request.user, created_at__gte=today).count() >= settings.TUTOR_AI_DAILY_LIMIT:
        return JsonResponse({'error':'Лимит вопросов на 24 часа исчерпан. Продолжите позже.'}, status=429)
    image = None
    upload = request.FILES.get('image')
    if upload:
        try:
            if upload.size > MAX_BYTES:
                raise ValueError('Изображение должно быть не больше 2 МиБ.')
            image = 'data:image/png;base64,' + base64.b64encode(canonical_image(upload.read(MAX_BYTES+1))).decode('ascii')
        except ValueError as exc:
            return JsonResponse({'error':str(exc)}, status=400)
    try:
        turn = TutorChatTurn.objects.create(user=request.user, kind=kind, slug=slug, request_id=request_id, question=question + ('\n[Приложено изображение]' if image else ''))
    except IntegrityError:
        return JsonResponse({'error':'Запрос уже обрабатывается.'}, status=409)
    history = list(turns.order_by('-created_at', '-pk')[:6])[::-1]
    try:
        answer = generate(build_messages(context, history, question, code, image))
    except TutorUnavailable as exc:
        turn.state = 'failed'
        turn.save(update_fields=['state'])
        return JsonResponse({'error':str(exc)}, status=503)
    turn.answer = answer
    turn.state = 'done'
    turn.save(update_fields=['answer', 'state'])
    return JsonResponse({'answer':answer, 'question':turn.question, 'id':str(request_id), 'solved':context['solved']})


@login_required
@never_cache
@require_http_methods(['POST'])
def assistant_transcribe(request):
    from tutorial.speech import available, transcribe, MAX_PCM
    if not available():
        return JsonResponse({'error':'Голосовой режим ещё не подключён.'}, status=503)
    audio = request.FILES.get('audio')
    if not audio or audio.size > MAX_PCM:
        return JsonResponse({'error':'Запись должна быть не длиннее 60 секунд.'}, status=400)
    try:
        return JsonResponse({'text':transcribe(audio.read(MAX_PCM+1))})
    except ValueError as exc:
        return JsonResponse({'error':str(exc)}, status=400)
    except TutorUnavailable as exc:
        return JsonResponse({'error':str(exc)}, status=503)


@login_required
@never_cache
@require_http_methods(['POST'])
def assistant_speak(request, turn_id):
    from django.shortcuts import get_object_or_404
    from django.http import HttpResponse
    from tutorial.speech import available, synthesize
    turn = get_object_or_404(TutorChatTurn, user=request.user, request_id=turn_id, state='done')
    if not available():
        return JsonResponse({'error':'Голосовой режим ещё не подключён.'}, status=503)
    try:
        return HttpResponse(synthesize(turn.answer), content_type='audio/wav')
    except TutorUnavailable as exc:
        return JsonResponse({'error':str(exc)}, status=503)
