import logging
import time
from urllib.parse import urlparse

from jnius import autoclass

from ..android_utils import share_by_intent
from ..android_utils import StartupState
from ..application import BaseActivity
from ..kolibri_utils import init_kolibri
from ..runnable import Runnable


PythonActivity = autoclass("org.kivy.android.PythonActivity")
KolibriAndroidHelper = autoclass("org.learningequality.KolibriAndroidHelper")

INITIAL_LOADING_PAGE_URL = "file:///android_asset/loadingScreen/index.html"
LOADING_PAGE_URL = "file:///android_asset/loadingScreen/index.html#/loading/default"


@Runnable
def configure_webview(*args):
    KolibriAndroidHelper.initialize(PythonActivity.mActivity)
    KolibriAndroidHelper.getInstance().configure(*args)


@Runnable
def replace_url_in_webview(url):
    KolibriAndroidHelper.getInstance().replaceUrl(url)


@Runnable
def show_loading_page(url):
    KolibriAndroidHelper.getInstance().showLoadingPage(url)


@Runnable
def set_app_key_cookie(url, app_key):
    KolibriAndroidHelper.getInstance().setAppKeyCookie(url, app_key)


def _build_kolibri_process_bus(application):
    from .kolibri_bus import AppPlugin
    from .kolibri_bus import KolibriAppProcessBus

    AppPlugin.register_share_file_interface(share_by_intent)

    kolibri_bus = KolibriAppProcessBus(enable_zeroconf=True)
    AppPlugin(kolibri_bus, application).subscribe()

    return kolibri_bus


class MainActivity(BaseActivity):
    TO_RUN_IN_MAIN = None
    _kolibri_bus = None
    _saved_kolibri_path = None
    _last_kolibri_path = None

    def __init__(self):
        super().__init__()

        configure_webview(
            Runnable(self._on_start_with_network),
            Runnable(self._on_loading_ready),
        )

    def on_activity_stopped(self, activity):
        super().on_activity_stopped(activity)

        if self._kolibri_bus is None:
            return

        if self._kolibri_bus.can_transition("IDLE"):
            # With some versions of Android, the onSaveInstanceState hook will
            # run after thsi one, so we need to keep track of the webview's
            # URL before switching to the loading screen.
            self._last_kolibri_path = self._get_current_kolibri_path()
            show_loading_page(LOADING_PAGE_URL)
            self._kolibri_bus.transition("IDLE")
        elif self._kolibri_bus.state != "IDLE":
            logging.warning(
                f"Kolibri is unable to stop because its state is '{self._kolibri_bus.state}"
            )

    def on_activity_resumed(self, activity):
        super().on_activity_resumed(activity)

        if self._kolibri_bus is None:
            return

        if self._kolibri_bus.can_transition("START"):
            self._last_kolibri_path = None
            show_loading_page(LOADING_PAGE_URL)
            self._kolibri_bus.transition("START")
        elif self._kolibri_bus.state != "START":
            logging.warning(
                f"Kolibri is unable to start because its state is '{self._kolibri_bus.state}'"
            )

    def on_activity_save_instance_state(self, activity, out_state_bundle):
        super().on_activity_save_instance_state(activity, out_state_bundle)

        if self._kolibri_bus is None:
            return

        kolibri_path = self._last_kolibri_path or self._get_current_kolibri_path()
        self._last_kolibri_path = None

        # Because of an issue with the on_activity_post_created method, we
        # have no way to receive saved state when the application starts. So,
        # we won't bother modifying out_state_bundle here. Instead, we will
        # simply save kolibri_path as a variable. This takes advantage of the
        # Python program continuing to run when the activity is stopped. If we
        # wanted to use the state bundle mechanism, it would look like:
        # out_state_bundle.putString("kolibri_path", kolibri_path)

        self._saved_kolibri_path = kolibri_path
        logging.info(f"Saved Kolibri path: '{kolibri_path or ''}'")

    def _get_current_kolibri_path(self):
        current_url = KolibriAndroidHelper.getInstance().getUrl()
        self._last_url = None

        if self._kolibri_bus.is_kolibri_url(current_url):
            return urlparse(current_url)._replace(scheme="", netloc="").geturl()
        else:
            return None

    def run(self):
        show_loading_page(INITIAL_LOADING_PAGE_URL)
        while True:
            if callable(self.TO_RUN_IN_MAIN):
                repeat = self.TO_RUN_IN_MAIN()
                if not repeat:
                    self.TO_RUN_IN_MAIN = None
                # Wait a bit after each main function call
                time.sleep(0.5)
            time.sleep(0.05)

    def get_saved_kolibri_path(self):
        return self._saved_kolibri_path

    def replace_url(self, url):
        replace_url_in_webview(url)

    def start_kolibri(self):
        # TODO: Wait until external storage is available
        #       <https://phabricator.endlessm.com/T33974>

        init_kolibri(debug=True)

        self._kolibri_bus = _build_kolibri_process_bus(self)
        app_key = self._kolibri_bus.get_app_key()
        logging.info(f"Setting app key cookie: {app_key}")
        # Android's CookieManager.setCookie awkwardly asks for a full URL, but
        # cookies generally apply across all ports for a given hostname, so it
        # is okay that we give it the expected hostname without specifying a
        # port.
        set_app_key_cookie("http://127.0.0.1", app_key)

        # start kolibri server
        logging.info("Starting kolibri server.")

        self._kolibri_bus.run()

    def _on_start_with_network(self):
        self.TO_RUN_IN_MAIN = self.start_kolibri

    def _on_loading_ready(self):
        startup_state = StartupState.get_current_state()
        if startup_state == StartupState.FIRST_TIME:
            logging.info("First time")
        else:
            logging.info("Starting network mode")
        self.TO_RUN_IN_MAIN = self.start_kolibri
