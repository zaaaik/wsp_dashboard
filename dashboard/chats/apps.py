from django.apps import AppConfig


class ChatsConfig(AppConfig):
    name = 'chats'

    def ready(self):
        from . import bloqueos  # noqa: F401  (registra las señales)
