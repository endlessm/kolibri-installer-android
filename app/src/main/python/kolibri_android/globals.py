import logging
import os
import sys
import traceback
from logging.config import dictConfig
from pathlib import Path

from jnius import autoclass

from .android_utils import get_log_root
from .android_utils import get_logging_config
from .android_utils import setup_analytics

SCRIPT_PATH = Path(__file__).absolute().parent.parent

FirebaseCrashlytics = autoclass("com.google.firebase.crashlytics.FirebaseCrashlytics")
PythonException = autoclass("org.learningequality.PythonException")
Arrays = autoclass("java.util.Arrays")


def initialize():
    # initialize logging before loading any third-party modules, as they may cause logging to get configured.
    log_root = get_log_root()
    os.makedirs(log_root, exist_ok=True)
    logging_config = get_logging_config(log_root, debug=True)
    dictConfig(logging_config)

    setup_analytics()

    sys.excepthook = log_exception


def log_exception(type, value, tb):
    logging.critical(str(value), exc_info=(type, value, tb))
    FirebaseCrashlytics.getInstance().recordException(
        PythonException(Arrays.toString(traceback.format_exception(type, value, tb)))
    )
