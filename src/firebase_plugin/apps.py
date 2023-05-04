import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class FirebaseConfig(AppConfig):
    name = "firebase_plugin"

    def ready(self):
        logger.info("Importing firebase_plugin signal handlers")
        from . import signals  # noqa: F401
