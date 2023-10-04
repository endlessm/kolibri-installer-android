import logging
import os

from android.content import Intent
from android.os import Parcelable
from android.util import Log
from androidx.core.content import FileProvider
from java import cast
from java.io import File
from java.lang import String
from org.endlessos.key import KolibriActivity


logger = logging.getLogger(__name__)

# Globals to keep references to Java objects
# See https://github.com/Android-for-Python/Android-for-Python-Users#pyjnius-memory-management
_send_intent = None


def get_activity():
    """Get the KolibriActivity instance

    Raises RuntimeError if the activity has not been created.
    """
    activity = KolibriActivity.getInstance()
    if activity is None:
        raise RuntimeError("KolibriActivity instance has not been created")
    return activity


def get_context():
    """Get the application component context

    Raises RuntimeError if it has not been set by the component.
    """
    context = KolibriActivity.getInstance()
    if context is not None:
        return context

    raise RuntimeError("Context has not been set from the application component")


def share_by_intent(path=None, filename=None, message=None, app=None, mimetype=None):
    global _send_intent

    assert (
        path or message or filename
    ), "Must provide either a path, a filename, or a msg to share"

    _send_intent = Intent()
    _send_intent.setAction(Intent.ACTION_SEND)
    context = get_context()
    if path:
        uri = FileProvider.getUriForFile(
            context,
            "org.endlessos.Key.fileprovider",
            File(path),
        )
        parcelable = cast(Parcelable, uri)
        _send_intent.putExtra(Intent.EXTRA_STREAM, parcelable)
        _send_intent.setType(String(mimetype or "*/*"))
        _send_intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    if message:
        if not path:
            _send_intent.setType(String(mimetype or "text/plain"))
        _send_intent.putExtra(Intent.EXTRA_TEXT, String(message))
    if app:
        _send_intent.setPackage(String(app))
    _send_intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    context.startActivity(_send_intent)
    _send_intent = None


class AndroidLogHandler(logging.Handler):
    """Logging handler dispatching to android.util.Log

    Converts Python logging records to Android log messages viewable
    with "adb logcat". The handler converts logging levels to log
    priorities, which allows filtering by priority with logcat or other
    Android log analysis tools.
    """

    def __init__(self, tag):
        super().__init__()

        self.tag = tag

    def emit(self, record):
        try:
            msg = self.format(record)
            priority = self.level_to_priority(record.levelno)
            Log.println(priority, self.tag, msg)
        except:  # noqa: E722
            self.handleError(record)

    @staticmethod
    def level_to_priority(level):
        if level >= logging.CRITICAL:
            return Log.ASSERT
        elif level >= logging.ERROR:
            return Log.ERROR
        elif level >= logging.WARNING:
            return Log.WARN
        elif level >= logging.INFO:
            return Log.INFO
        elif level >= logging.DEBUG:
            return Log.DEBUG
        else:
            return Log.VERBOSE


def get_logging_config(LOG_ROOT, debug=False, debug_database=False):
    """Logging configuration

    This is customized from
    kolibri.utils.logger.get_default_logging_config(), which is the
    basis for the logging configuration used in Kolibri.
    """
    # This is the general level
    DEFAULT_LEVEL = "INFO" if not debug else "DEBUG"
    DATABASE_LEVEL = "INFO" if not debug_database else "DEBUG"
    DEFAULT_HANDLERS = ["android", "file"]

    return {
        "version": 1,
        "disable_existing_loggers": False,
        # No filters are used here, but kolibri adds some and expects
        # the top level filters dict to exist.
        "filters": {},
        "formatters": {
            "simple": {
                "format": "%(name)s: %(message)s",
            },
            "full": {
                "format": "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "android": {
                "class": "kolibri_android.android_utils.AndroidLogHandler",
                "tag": "EndlessKey",
                # Since Android logging already has timestamps and priority levels, they
                # aren't needed here.
                "formatter": "simple",
            },
            "file": {
                # Kolibri uses a customized version of
                # logging.handlers.TimedRotatingFileHandler. We don't
                # want to use that here to avoid importing kolibri too
                # early. IMO, the regular rotating handler based on size
                # is better in the Android case so the total disk space
                # used for logs is managed.
                "class": "logging.handlers.RotatingFileHandler",
                "filename": os.path.join(LOG_ROOT, "kolibri.txt"),
                "maxBytes": 5 << 20,  # 5 Mib
                "backupCount": 5,
                "formatter": "full",
            },
        },
        "loggers": {
            "": {
                "handlers": DEFAULT_HANDLERS,
                "level": DEFAULT_LEVEL,
            },
            "kolibri_android": {
                # Always log our code at debug level.
                "level": "DEBUG",
            },
            "jnius": {
                # jnius debug logs are very noisy, so limit it to info.
                "level": "INFO",
            },
            "kolibri": {
                # kolibri expects the handlers list to exist so it can
                # append django's email handler.
                "handlers": [],
            },
            # For now, we do not fetch debugging output from this
            # We should introduce custom debug log levels or log
            # targets, i.e. --debug-level=high
            "kolibri.core.tasks.worker": {
                "level": "INFO",
            },
            "django": {
                # kolibri expects the handlers list to exist so it can
                # append django's email handler.
                "handlers": [],
            },
            "django.db.backends": {
                "level": DATABASE_LEVEL,
            },
            "django.request": {
                # kolibri expects the handlers list to exist so it can
                # append django's email handler.
                "handlers": [],
            },
            "django.template": {
                # Django template debug is very noisy, only log INFO and above.
                "level": "INFO",
            },
        },
    }
