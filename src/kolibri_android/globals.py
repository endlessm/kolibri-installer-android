import logging
import os
import sys

from kolibri_android.android_utils import get_timezone_name

_file_dir = os.path.dirname(os.path.abspath(__file__))
PACKAGE_DIR = os.path.abspath(os.path.join(_file_dir, ".."))


def initialize():
    # initialize logging before loading any third-party modules, as they may cause logging to get configured.
    logging.basicConfig(level=logging.DEBUG)

    sys.path.append(PACKAGE_DIR)
    sys.path.append(os.path.join(PACKAGE_DIR, "extra-packages"))
    sys.path.append(os.path.join(PACKAGE_DIR, "kolibri", "dist"))

    os.environ["TZ"] = get_timezone_name()
    os.environ["LC_ALL"] = "en_US.UTF-8"
