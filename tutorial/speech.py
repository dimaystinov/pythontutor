"""Speech providers used by the owner's Zachet installation; audio is not stored."""
import io
import re
import wave
from urllib.parse import urlencode
import requests
from django.conf import settings
from tutorial.ai_tutor import TutorUnavailable

SAMPLE_RATE = 16000
MAX_PCM = SAMPLE_RATE * 2 * 60


def available():
    return bool(settings.TUTOR_NVIDIA_API_KEY and (settings.TUTOR_TTS_PROVIDER == 'nvidia' or settings.TUTOR_YANDEX_SPEECHKIT_API_KEY))


def transcribe(pcm):
    if not pcm or len(pcm) % 2 or len(pcm) > MAX_PCM:
        raise ValueError('Запишите от 1 до 60 секунд речи.')
    import riva.client
    auth = None
    future = None
    try:
        auth = riva.client.Auth(uri='grpc.nvcf.nvidia.com:443', use_ssl=True, metadata_args=[['function-id','b702f636-f60c-4a3d-a6f4-f3568c13bd7d'], ['authorization', 'Bearer ' + settings.TUTOR_NVIDIA_API_KEY]])
        output = io.BytesIO()
        with wave.open(output, 'wb') as wav:
            wav.setparams((1, 2, SAMPLE_RATE, 0, 'NONE', 'not compressed'))
            wav.writeframes(pcm)
        service = riva.client.ASRService(auth)
        config = riva.client.RecognitionConfig(language_code='ru', max_alternatives=1, enable_automatic_punctuation=True)
        future = service.offline_recognize(output.getvalue(), config, future=True)
        response = future.result(timeout=25)
        text = ' '.join(result.alternatives[0].transcript.strip() for result in response.results if result.alternatives).strip()
        if not text:
            raise TutorUnavailable('Речь не распознана. Попробуйте говорить ближе к микрофону.')
        return text[:3000]
    except TutorUnavailable:
        raise
    except Exception:
        raise TutorUnavailable('Распознавание речи временно недоступно. Можно написать вопрос текстом.') from None
    finally:
        if future is not None and not future.done():
            future.cancel()
        if auth is not None:
            auth.channel.close()


def synthesize(answer):
    if settings.TUTOR_TTS_PROVIDER == 'nvidia':
        return synthesize_nvidia(answer)
    return synthesize_yandex(answer)


def synthesize_yandex(answer):
    # Do not read long source listings aloud; they remain available in the chat.
    text = re.sub(r'```[\s\S]*?```', ' Пример кода показан в чате. ', answer)
    text = re.sub(r'[*#`]', '', text).strip()[:1800]
    data = {'text':text, 'lang':'ru-RU', 'voice':settings.TUTOR_YANDEX_SPEECHKIT_VOICE, 'speed':'1.0', 'format':'lpcm', 'sampleRateHertz':'48000'}
    if not text or len(urlencode(data).encode()) > 15000:
        raise TutorUnavailable('Этот ответ слишком длинный для озвучивания. Прочитайте его в чате.')
    try:
        with requests.Session() as client:
            client.trust_env = False
            with client.post('https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize', headers={'Authorization':'Api-Key '+settings.TUTOR_YANDEX_SPEECHKIT_API_KEY}, data=data, timeout=(8,30), allow_redirects=False, stream=True) as response:
                if response.status_code != 200:
                    raise TutorUnavailable('Озвучивание временно недоступно. Текст ответа сохранён в чате.')
                chunks=[]; size=0
                for chunk in response.iter_content(32768):
                    size += len(chunk)
                    if size > 16000000:
                        raise TutorUnavailable('Ответ слишком длинный для озвучивания.')
                    chunks.append(chunk)
                pcm=b''.join(chunks)
        if not pcm or len(pcm)%2:
            raise ValueError
        out=io.BytesIO()
        with wave.open(out,'wb') as wav:
            wav.setparams((1,2,48000,0,'NONE','not compressed'))
            wav.writeframes(pcm)
        return out.getvalue()
    except (requests.RequestException, ValueError):
        raise TutorUnavailable('Озвучивание временно недоступно. Текст ответа сохранён в чате.') from None


def synthesize_nvidia(answer):
    import riva.client
    text = re.sub(r'```[\s\S]*?```', ' Пример кода показан в чате. ', answer)
    text = re.sub(r'[*#`]', '', text).strip()[:1800]
    if not text:
        raise TutorUnavailable('Нет текста для озвучивания.')
    auth = None
    future = None
    try:
        auth = riva.client.Auth(uri='grpc.nvcf.nvidia.com:443', use_ssl=True, metadata_args=[['function-id', 'ddacc747-1269-4fab-bfd9-8f593dead106'], ['authorization', 'Bearer ' + settings.TUTOR_NVIDIA_API_KEY]])
        service = riva.client.SpeechSynthesisService(auth)
        chunks = []
        # Chatterbox accepts at most 500 characters per request.
        while text:
            end = min(450, len(text))
            if end < len(text):
                boundary = max(text.rfind('. ', 0, end), text.rfind(' ', 0, end))
                if boundary > 100:
                    end = boundary + 1
            part, text = text[:end], text[end:].strip()
            future = service.synthesize(part, voice_name='Chatterbox-Multilingual.ru-RU.Male', language_code='ru-RU', sample_rate_hz=24000, future=True)
            chunks.append(future.result(timeout=25).audio)
        pcm = b''.join(chunks)
        if not pcm or len(pcm) % 2 or len(pcm) > 16000000:
            raise ValueError('Invalid audio')
        out = io.BytesIO()
        with wave.open(out, 'wb') as wav:
            wav.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
            wav.writeframes(pcm)
        return out.getvalue()
    except Exception:
        raise TutorUnavailable('Озвучивание временно недоступно. Текст ответа сохранён в чате.') from None
    finally:
        if future is not None and not future.done():
            future.cancel()
        if auth is not None:
            auth.channel.close()
