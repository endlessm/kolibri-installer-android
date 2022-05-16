import importlib
import logging
import os

import initialization  # noqa: F401 keep this first, to ensure we're set up for other imports
from android_utils import share_by_intent
from android_utils import start_service
from jnius import autoclass
from kolibri.plugins import config as plugins_config
from kolibri.plugins.app.utils import interface
from kolibri.plugins.registry import registered_plugins
from kolibri.plugins.utils import disable_plugin
from kolibri.plugins.utils import enable_plugin
from kolibri.utils.cli import initialize
from kolibri.utils.server import BaseKolibriProcessBus
from kolibri.utils.server import KolibriServerPlugin
from kolibri.utils.server import ZeroConfPlugin
from kolibri.utils.server import ZipContentServerPlugin
from magicbus.plugins import SimplePlugin
from runnable import Runnable

# These Kolibri plugins conflict with the plugins listed in REQUIRED_PLUGINS
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


def _disable_kolibri_plugin(plugin_name: str) -> bool:
    if plugin_name in plugins_config.ACTIVE_PLUGINS:
        logging.info(f"Disabling plugin {plugin_name}")
        disable_plugin(plugin_name)

    return True


def _enable_kolibri_plugin(plugin_name: str, optional=False) -> bool:
    if optional and not importlib.util.find_spec(plugin_name):
        return False

    if plugin_name not in plugins_config.ACTIVE_PLUGINS:
        logging.info(f"Enabling plugin {plugin_name}")
        registered_plugins.register_plugins([plugin_name])
        enable_plugin(plugin_name)

    return True


PythonActivity = autoclass("org.kivy.android.PythonActivity")

loadUrl = Runnable(PythonActivity.mWebView.loadUrl)


class AppPlugin(SimplePlugin):
    def __init__(self, bus):
        self.bus = bus
        self.bus.subscribe("SERVING", self.SERVING)

    def SERVING(self, port):
        start_url = (
            "http://127.0.0.1:{port}".format(port=port) + interface.get_initialize_url()
        )
        loadUrl(start_url)


logging.info("Initializing Kolibri and running any upgrade routines")

loadUrl("file:///android_asset/_load.html")

for plugin_name in DISABLED_PLUGINS:
    _disable_kolibri_plugin(plugin_name)

for plugin_name in REQUIRED_PLUGINS:
    _enable_kolibri_plugin(plugin_name)

for plugin_name in OPTIONAL_PLUGINS:
    _enable_kolibri_plugin(plugin_name, optional=True)

# we need to initialize Kolibri to allow us to access the app key
initialize()

interface.register(share_file=share_by_intent)

# start kolibri server
logging.info("Starting kolibri server.")

kolibri_server = BaseKolibriProcessBus()
# Setup zeroconf plugin
zeroconf_plugin = ZeroConfPlugin(kolibri_server, kolibri_server.port)
zeroconf_plugin.subscribe()
kolibri_server = KolibriServerPlugin(
    kolibri_server,
    kolibri_server.port,
)

alt_port_server = ZipContentServerPlugin(
    kolibri_server,
    kolibri_server.zip_port,
)
# Subscribe these servers
kolibri_server.subscribe()
alt_port_server.subscribe()
app_plugin = AppPlugin(kolibri_server)
app_plugin.subscribe()
start_service("workers")
kolibri_server.run()
