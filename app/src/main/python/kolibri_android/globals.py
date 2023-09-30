import os
from logging.config import dictConfig
from pathlib import Path

from .android_utils import get_log_root
from .android_utils import get_logging_config
from .android_utils import setup_analytics

PACKAGE_PATH = Path(__file__).absolute().parent


def initialize():
    # initialize logging before loading any third-party modules, as they may cause logging to get configured.
    log_root = get_log_root()
    os.makedirs(log_root, exist_ok=True)
    logging_config = get_logging_config(log_root, debug=True)
    dictConfig(logging_config)

    setup_analytics()
