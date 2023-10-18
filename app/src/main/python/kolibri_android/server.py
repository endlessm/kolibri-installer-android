import logging

from kolibri.core.device.models import DeviceAppKey
from kolibri.plugins.app.utils import interface
from kolibri.utils.server import BaseKolibriProcessBus
from kolibri.utils.server import KolibriServerPlugin
from kolibri.utils.server import ServicesPlugin
from kolibri.utils.server import ZeroConfPlugin
from kolibri.utils.server import ZipContentServerPlugin

from .android_utils import share_file

logger = logging.getLogger(__name__)


class ServerProcessBus(BaseKolibriProcessBus):
    def __init__(self, *args, enable_zeroconf=True, **kwargs):
        super().__init__(*args, **kwargs)

        # Wire up the share_file interface.
        interface.register(share_file=share_file)

        ServicesPlugin(self).subscribe()

        if enable_zeroconf:
            ZeroConfPlugin(self, self.port).subscribe()

        KolibriServerPlugin(self, self.port).subscribe()

        ZipContentServerPlugin(self, self.zip_port).subscribe()

    def start(self):
        logger.info("Starting bus")
        self.graceful()

    def stop(self):
        logger.info("Stopping bus")
        self.transition("EXITED")

    def get_url(self):
        if self.state != "RUN":
            raise RuntimeError("Bus not running")
        return f"http://127.0.0.1:{self.port}/"

    def get_app_key(self):
        return DeviceAppKey.get_app_key()
