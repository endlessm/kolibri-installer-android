import http.server
import importlib
import json
import logging
import os
import time

import initialization  # noqa: F401 keep this first, to ensure we're set up for other imports
from android.runnable import run_on_ui_thread
from android_utils import ask_all_files_access
from android_utils import get_endless_key_paths
from android_utils import provision_endless_key_database
from android_utils import start_service
from jnius import autoclass
from kolibri.plugins import config as plugins_config
from kolibri.plugins.app.utils import interface
from kolibri.plugins.registry import registered_plugins
from kolibri.plugins.utils import disable_plugin
from kolibri.plugins.utils import enable_plugin
from kolibri.utils.cli import initialize
from kolibri.utils.server import _read_pid_file
from kolibri.utils.server import PID_FILE
from kolibri.utils.server import STATUS_RUNNING
from kolibri.utils.server import wait_for_status
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


access_granted = ask_all_files_access()
if access_granted:
    endless_key_paths = get_endless_key_paths()
    provision_endless_key_database(endless_key_paths)

PythonActivity = autoclass("org.kivy.android.PythonActivity")

loadUrl = Runnable(PythonActivity.mWebView.loadUrl)

logging.info("Initializing Kolibri and running any upgrade routines")

loadUrl("file:///android_asset/_load.html")

for plugin_name in DISABLED_PLUGINS:
    _disable_kolibri_plugin(plugin_name)

for plugin_name in REQUIRED_PLUGINS:
    _enable_kolibri_plugin(plugin_name)

for plugin_name in OPTIONAL_PLUGINS:
    _enable_kolibri_plugin(plugin_name, optional=True)

# Ensure that the pidfile is removed on startup
try:
    os.unlink(PID_FILE)
except FileNotFoundError:
    pass


def start_kolibri():
    # we need to initialize Kolibri to allow us to access the app key
    initialize()

    # start kolibri server
    logging.info("Starting kolibri server via Android service...")
    start_service("server")

    # Tie up this thread until the server is running
    wait_for_status(STATUS_RUNNING, timeout=120)

    _, port, _, _ = _read_pid_file(PID_FILE)

    start_url = (
        "http://127.0.0.1:{port}".format(port=port) + interface.get_initialize_url()
    )
    loadUrl(start_url)

    start_service("remoteshell")


@run_on_ui_thread
def hook():
    PythonActivity.mWebView.setWebContentsDebuggingEnabled(True)
    endlessAPI = """
window.EndlessAPI = {
    load: () => {
        fetch('http://localhost:8000/load');
    },

    loadWithUSB: () => {
        fetch('http://localhost:8000/loadWithUSB');
    },
};

"""
    PythonActivity.mWebView.evaluateJavascript(endlessAPI, None)
    PythonActivity.mWebView.evaluateJavascript("show_welcome()", None)


hook()


class HandlerClass(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        logging.info(f"Starting kolibri backend with {self.path}")
        start_kolibri()

        self.send_response(200)
        self.send_header("Content-type", "text/json")
        self.end_headers()
        httpd.shutdown()
        self.wfile.write(json.dumps({}).encode())


server_address = ("", 8000)
httpd = http.server.HTTPServer(server_address, HandlerClass)
httpd.serve_forever()


while True:
    time.sleep(0.05)
