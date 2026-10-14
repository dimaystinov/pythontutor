from django.conf import settings
from tutorial.learning_context import LEARNING_CONTEXT

def execution(request):
    return {'tutor_learning_context': LEARNING_CONTEXT, 'execution_mode': settings.EXECUTION_MODE, 'pwa_offline':getattr(request,'pwa_offline',False)}
