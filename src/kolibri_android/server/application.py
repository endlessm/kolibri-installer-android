import logging
import os

from kolibri_android.android_utils import make_service_foreground
from kolibri_android.android_utils import share_by_intent
from kolibri_android.android_utils import get_service
from kolibri_android.server.kolibri_utils import init_kolibri

from jnius import autoclass
from kolibri.dist.magicbus.plugins import SimplePlugin

AndroidString = autoclass("java.lang.String")
Context = autoclass("android.content.Context")
Intent = autoclass("android.content.Intent")
PythonActivity = autoclass("org.kivy.android.PythonActivity")
Uri = autoclass("android.net.Uri")


class Application(object):
    def run(self):
        logging.info("Entering Kolibri server service")

        # ensure the service stays running by "foregrounding" it with a persistent notification
        make_service_foreground("Kolibri is running...", "Click here to resume.")

        init_kolibri()

        from kolibri.plugins.app.utils import interface
        from kolibri.utils.conf import KOLIBRI_HOME
        from kolibri.utils.server import KolibriProcessBus

        kolibri_bus = KolibriProcessBus(
            port=0,
            zip_port=0,
            background=False,
        )

        kolibri_android_plugin = _KolibriAndroidPlugin(kolibri_bus)
        kolibri_android_plugin.subscribe()

        # register app capabilities
        interface.register(share_file=share_by_intent)

        logging.info("Home folder: {}".format(KOLIBRI_HOME))
        logging.info("Timezone: {}".format(os.environ.get("TZ", "(default)")))

        # start the kolibri server
        kolibri_bus.run()


class _KolibriAndroidPlugin(SimplePlugin):
    def __init__(self, bus):
        self.bus = bus
        self.bus.subscribe("SERVING", self.SERVING)

    def SERVING(self, port):
        from kolibri.plugins.app.utils import interface
        from kolibri.utils.server import get_urls

        _, base_urls = get_urls(listen_port=port)
        base_url = base_urls[0]
        initialize_url = interface.get_initialize_url()

        service = get_service()
        app_context = service.getApplication().getApplicationContext()

        start_intent = Intent()
        start_intent.setPackage("org.endlessos.Key")
        start_intent.setAction("org.endlessos.Key.SERVING")
        start_intent.putExtra("baseUrl", AndroidString(base_url or ""))
        start_intent.putExtra("initializeUrl", AndroidString(initialize_url or ""))

        app_context.sendBroadcast(start_intent)
