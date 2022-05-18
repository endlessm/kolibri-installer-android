from kolibri.utils.server import BaseKolibriProcessBus
from kolibri.utils.server import KolibriServerPlugin
from kolibri.utils.server import ZeroConfPlugin
from kolibri.utils.server import ZipContentServerPlugin


class KolibriAppProcessBus(BaseKolibriProcessBus):
    def __init__(self, *args, enable_zeroconf=True, **kwargs):
        super(KolibriAppProcessBus, self).__init__(*args, **kwargs)

        if enable_zeroconf:
            ZeroConfPlugin(self, self.port).subscribe()

        KolibriServerPlugin(
            self,
            self.port,
        ).subscribe()

        ZipContentServerPlugin(
            self,
            self.zip_port,
        ).subscribe()
