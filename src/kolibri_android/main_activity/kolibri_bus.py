from urllib.parse import urljoin
from urllib.parse import urlparse

from kolibri.core.device.models import DeviceAppKey
from kolibri.plugins.app.utils import interface
from kolibri.utils.server import BaseKolibriProcessBus
from kolibri.utils.server import get_urls
from kolibri.utils.server import KolibriServerPlugin
from kolibri.utils.server import ServicesPlugin
from kolibri.utils.server import ZeroConfPlugin
from kolibri.utils.server import ZipContentServerPlugin
from magicbus.plugins import SimplePlugin


class KolibriAppProcessBus(BaseKolibriProcessBus):
    def __init__(self, *args, enable_zeroconf=True, **kwargs):
        super(KolibriAppProcessBus, self).__init__(*args, **kwargs)

        ServicesPlugin(self).subscribe()

        if enable_zeroconf:
            ZeroConfPlugin(self, self.port).subscribe()

        AndroidKolibriServerPlugin(self, self.port).subscribe()

        AndroidZipContentServerPlugin(self, self.zip_port).subscribe()

    def get_app_key(self):
        return DeviceAppKey.get_app_key()

    def is_kolibri_url(self, url):
        if not url:
            return False

        if not self.port:
            return False

        _, server_urls = get_urls(self.port)

        if not server_urls:
            return False

        url_parts = urlparse(url)

        for server_url in server_urls:
            server_url_parts = urlparse(server_url)
            if (
                url_parts.scheme == server_url_parts.scheme
                and url_parts.netloc == server_url_parts.netloc
            ):
                return True

        return False

    def can_transition(self, to_state: str) -> bool:
        return (self.state, to_state) in self.transitions


class AppPlugin(SimplePlugin):
    def __init__(self, bus, application):
        self.application = application
        self.bus = bus
        self.bus.subscribe("SERVING", self.SERVING)

    @staticmethod
    def register_share_file_interface(share_file):
        interface.register(share_file=share_file)

    def SERVING(self, port):
        base_url = "http://127.0.0.1:{port}".format(port=port)
        next_url = self.application.get_saved_kolibri_path() or ""
        start_url = urljoin(base_url, next_url)
        self.application.replace_url(start_url)


class AndroidKolibriServerPlugin(KolibriServerPlugin):
    @property
    def application(self):
        from kolibri_android.kolibri_extra.wsgi import application

        return application


class AndroidZipContentServerPlugin(ZipContentServerPlugin):
    @property
    def application(self):
        from kolibri_android.kolibri_extra.alt_wsgi import alt_application

        return alt_application
