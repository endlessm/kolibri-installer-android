import logging

from jnius import autoclass
from kolibri.dist.magicbus.plugins import SimplePlugin

from ..android_utils import share_by_intent
from ..android_utils import start_service
from ..runnable import Runnable

PythonActivity = autoclass("org.kivy.android.PythonActivity")

loadUrl = Runnable(PythonActivity.mWebView.loadUrl)


class AppPlugin(SimplePlugin):
    def __init__(self, bus):
        self.bus = bus
        self.bus.subscribe("SERVING", self.SERVING)

    def SERVING(self, port):
        from kolibri.plugins.app.utils import interface

        start_url = (
            "http://127.0.0.1:{port}".format(port=port) + interface.get_initialize_url()
        )
        loadUrl(start_url)


class Application(object):
    def run(self):
        # start kolibri server
        logging.info("Starting kolibri server...")

        # TODO: Require Kolibri >= 0.16

        _init_kolibri()
        _register_share_interface()
        self.__run_kolibri_server()

    def __run_kolibri_server(self):
        from .kolibri_bus import KolibriAppProcessBus

        kolibri_server = KolibriAppProcessBus(enable_zeroconf=False)

        AppPlugin(kolibri_server).subscribe()

        start_service("workers")
        kolibri_server.run()


def _init_kolibri(**kwargs):
    from ..kolibri_utils import init_kolibri

    init_kolibri(**kwargs)


def _register_share_interface():
    from kolibri.plugins.app.utils import interface

    interface.register(share_file=share_by_intent)
