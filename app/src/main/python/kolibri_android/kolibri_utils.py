import logging
import os
from importlib.util import find_spec
from logging.config import dictConfig
from pathlib import Path

from .android_utils import get_logging_config

logger = logging.getLogger(__name__)

PACKAGE_PATH = Path(__file__).absolute().parent

kolibri_initialized = False

# These Kolibri plugins conflict with the plugins listed in REQUIRED_PLUGINS
# or OPTIONAL_PLUGINS:
DISABLED_PLUGINS = [
    "kolibri.plugins.learn",
]

# These Kolibri plugins must be enabled for the application to function
# correctly:
REQUIRED_PLUGINS = [
    "kolibri.plugins.app",
    "kolibri_android.plugin",
]

# These Kolibri plugins will be dynamically enabled if they are available:
OPTIONAL_PLUGINS = [
    "kolibri_explore_plugin",
    "kolibri_zim_plugin",
]


def initialize(
    kolibri_home: str,
    kolibri_run_mode: str,
    version_name: str,
    timezone: str,
    node_id: str,
    debug: bool = False,
    **kwargs,
):
    global kolibri_initialized
    if kolibri_initialized:
        logger.info("Skipping Kolibri setup")
        return

    log_root = os.path.join(kolibri_home, "logs")
    os.makedirs(log_root, exist_ok=True)
    logging_config = get_logging_config(log_root, debug=debug)
    dictConfig(logging_config)

    logger.info("Initializing Kolibri and running any upgrade routines")

    # if there's no database in the home folder this is the first launch
    db_path = os.path.join(kolibri_home, "db.sqlite3")
    if not os.path.exists(db_path):
        logger.info("First time initialization")

    _init_kolibri_env(kolibri_home, kolibri_run_mode, version_name, timezone, node_id)

    _monkeypatch_kolibri_logging()

    for plugin_name in DISABLED_PLUGINS:
        _kolibri_disable_plugin(plugin_name)

    for plugin_name in REQUIRED_PLUGINS:
        _kolibri_enable_plugin(plugin_name)

    for plugin_name in OPTIONAL_PLUGINS:
        _kolibri_enable_plugin(plugin_name, optional=True)

    _kolibri_initialize(debug=debug, **kwargs)

    kolibri_initialized = True


def _init_kolibri_env(
    kolibri_home: str, run_mode: str, version_name: str, timezone: str, node_id: str
):
    os.environ["KOLIBRI_HOME"] = kolibri_home
    os.environ["KOLIBRI_RUN_MODE"] = run_mode
    os.environ["KOLIBRI_PROJECT"] = "endless-key-android"
    os.environ["KOLIBRI_APK_VERSION_NAME"] = version_name
    os.environ["TZ"] = timezone
    os.environ["LC_ALL"] = "en_US.UTF-8"

    os.environ["DJANGO_SETTINGS_MODULE"] = "kolibri_android.kolibri_extra.settings"

    # Unfortunately, some packages use the presence of p4a's ANDROID_ARGUMENT
    # environment variable to detect if they're on Android.
    os.environ["ANDROID_ARGUMENT"] = ""

    AUTOPROVISION_PATH = PACKAGE_PATH.joinpath("automatic_provision.json")
    if AUTOPROVISION_PATH.is_file():
        os.environ["KOLIBRI_AUTOMATIC_PROVISION_FILE"] = AUTOPROVISION_PATH.as_posix()

    os.environ["KOLIBRI_CHERRYPY_THREAD_POOL"] = "2"

    os.environ["KOLIBRI_APPS_BUNDLE_PATH"] = PACKAGE_PATH.joinpath("apps").as_posix()
    os.environ["KOLIBRI_CONTENT_COLLECTIONS_PATH"] = PACKAGE_PATH.joinpath(
        "collections"
    ).as_posix()

    # Don't set this if the retrieved id is falsy, too short, or a specific
    # id that is known to be hardcoded in many devices.
    if node_id and len(node_id) >= 16 and node_id != "9774d56d682e549c":
        os.environ["MORANGO_NODE_ID"] = node_id


def _monkeypatch_kolibri_logging():
    """Monkeypatch kolibri.utils.logger.get_default_logging_config

    Currently this is the only way to fully customize logging in
    kolibri. Custom Django LOG settings can be used, but that's only
    applied later when django is initialized.
    """
    import kolibri.utils.logger

    logger.info("Monkeypatching kolibri get_default_logging_config")
    kolibri.utils.logger.get_default_logging_config = get_logging_config


def _kolibri_initialize(**kwargs):
    from kolibri.utils.main import initialize

    initialize(**kwargs)


def _kolibri_disable_plugin(plugin_name: str) -> bool:
    from kolibri.main import disable_plugin
    from kolibri.plugins import config as plugins_config

    if plugin_name in plugins_config.ACTIVE_PLUGINS:
        logger.info(f"Disabling plugin {plugin_name}")
        disable_plugin(plugin_name)

    return True


def _kolibri_enable_plugin(plugin_name: str, optional=False) -> bool:
    from kolibri.main import enable_plugin
    from kolibri.plugins import config as plugins_config

    if optional and not find_spec(plugin_name):
        return False

    if plugin_name not in plugins_config.ACTIVE_PLUGINS:
        logger.info(f"Enabling plugin {plugin_name}")
        enable_plugin(plugin_name)

    return True
