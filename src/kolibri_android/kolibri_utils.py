import importlib.util
import logging
import os
import re

from .android_utils import apply_android_workarounds
from .android_utils import get_android_id
from .android_utils import get_home_folder
from .android_utils import get_signature_key_issuing_organization
from .android_utils import get_version_name
from .globals import PACKAGE_DIR


# These Kolibrikolibri_android plugins conflict with the plugins listed in REQUIRED_PLUGINS
# or OPTIONAL_PLUGINS:
DISABLED_PLUGINS = [
    "kolibri.plugins.learn",
]

# These Kolibri plugins must be enabled for the application to function
# correctly:
REQUIRED_PLUGINS = [
    "kolibri.plugins.app",
]

# These Kolibri plugins will be dynamically enabled if they are available:
OPTIONAL_PLUGINS = [
    "kolibri_explore_plugin",
]


def init_kolibri(**kwargs):
    apply_android_workarounds()

    _init_kolibri_env()
    _clear_kolibri_pid()

    from kolibri.utils.main import initialize

    for plugin_name in DISABLED_PLUGINS:
        _disable_kolibri_plugin(plugin_name)

    for plugin_name in REQUIRED_PLUGINS:
        _enable_kolibri_plugin(plugin_name)

    for plugin_name in OPTIONAL_PLUGINS:
        _enable_kolibri_plugin(plugin_name, optional=True)

    initialize(**kwargs)


def _clear_kolibri_pid():
    from kolibri.utils.server import PID_FILE

    # Ensure that the pidfile is removed on startup
    try:
        os.unlink(PID_FILE)
    except FileNotFoundError:
        pass


def _init_kolibri_env():
    os.environ["KOLIBRI_RUN_MODE"] = _get_run_mode()
    os.environ["KOLIBRI_APK_VERSION_NAME"] = get_version_name()
    os.environ["KOLIBRI_HOME"] = get_home_folder()
    os.environ["DJANGO_SETTINGS_MODULE"] = "kolibri_android.kolibri_settings"

    AUTOPROVISION_FILE = os.path.join(PACKAGE_DIR, "automatic_provision.json")
    if os.path.exists(AUTOPROVISION_FILE):
        os.environ["KOLIBRI_AUTOMATIC_PROVISION_FILE"] = AUTOPROVISION_FILE

    os.environ["KOLIBRI_CHERRYPY_THREAD_POOL"] = "2"

    os.environ["KOLIBRI_APPS_BUNDLE_PATH"] = os.path.join(
        PACKAGE_DIR, "apps-bundle", "apps"
    )

    android_id = get_android_id()
    if android_id:
        os.environ["MORANGO_NODE_ID"] = android_id


def _get_run_mode():
    signing_org = get_signature_key_issuing_organization()
    if signing_org == "Learning Equality":
        return "android-testing"
    elif signing_org == "Android":
        return "android-debug"
    elif signing_org == "Google Inc.":
        return ""  # Play Store!
    else:
        return "android-" + re.sub(r"[^a-z ]", "", signing_org.lower()).replace(
            " ", "-"
        )


def _disable_kolibri_plugin(plugin_name):
    from kolibri.plugins import config as plugins_config
    from kolibri.plugins.utils import disable_plugin

    if plugin_name in plugins_config.ACTIVE_PLUGINS:
        logging.info(f"Disabling plugin {plugin_name}")
        disable_plugin(plugin_name)


def _enable_kolibri_plugin(plugin_name, optional=False):
    from kolibri.plugins import config as plugins_config
    from kolibri.plugins.registry import registered_plugins
    from kolibri.plugins.utils import enable_plugin

    if optional and not importlib.util.find_spec(plugin_name):
        return

    if plugin_name not in plugins_config.ACTIVE_PLUGINS:
        logging.info(f"Enabling plugin {plugin_name}")
        registered_plugins.register_plugins([plugin_name])
        enable_plugin(plugin_name)
