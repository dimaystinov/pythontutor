from django.apps import AppConfig

class TutorialConfig(AppConfig):
    name = 'tutorial'

    def ready(self):
        from . import signals  # noqa: F401
