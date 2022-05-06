import logging
import time
from urllib.parse import urljoin

from android.broadcast import BroadcastReceiver
from jnius import autoclass

from kolibri_android.android_utils import start_service
from kolibri_android.runnable import Runnable

PythonActivity = autoclass("org.kivy.android.PythonActivity")

loadUrl = Runnable(PythonActivity.mWebView.loadUrl)

class Application(object):
    def run(self):
        logging.info("Initializing Kolibri and running any upgrade routines")

        loadUrl("file:///android_asset/_load.html")

        broadcast_receiver = BroadcastReceiver(
            self.__on_receive, actions=["org.endlessos.Key.SERVING"]
        )
        broadcast_receiver.start()

        # start kolibri server
        logging.info("Starting kolibri server via Android service...")
        start_service("server")

        while True:
            time.sleep(0.05)

    def __on_receive(self, context, intent):
        extras = intent.getExtras()
        base_url = extras.getString("baseUrl")
        initialize_url = extras.getString("initializeUrl")
        loadUrl(urljoin(base_url, initialize_url))
