import os
import sys
import tempfile
from unittest import TestCase
from unittest.mock import DEFAULT
from unittest.mock import MagicMock
from unittest.mock import patch

# TODO: Only mock these modules when Android is unavailable
android_mock = MagicMock()
jnius_mock = MagicMock()
runnable_mock = MagicMock()


@patch.dict(
    sys.modules,
    {
        "android.activity": android_mock,
        "jnius": jnius_mock,
        "kolibri_android.runnable": runnable_mock,
    },
)
class MainActivityTestCase(TestCase):
    def setUp(self):
        self.kolibri_home_tempdir = tempfile.TemporaryDirectory()
        os.environ["KOLIBRI_HOME"] = self.kolibri_home_tempdir.name

    def tearDown(self):
        self.kolibri_home_tempdir.cleanup()
        self.kolibri_home_tempdir = None

    @patch.multiple(
        "kolibri_android.android_utils",
        configure_webview=DEFAULT,
        get_signature_key_issuing_organization=DEFAULT,
        get_timezone_name=DEFAULT,
        get_version_name=DEFAULT,
        get_endless_key_uris=DEFAULT,
        get_home_folder=DEFAULT,
    )
    @patch.multiple(
        "kolibri_android.main_activity.kolibri_bus.KolibriAppProcessBus",
        run=DEFAULT,
    )
    def test_activity_run(self, **mocks):
        mocks["get_signature_key_issuing_organization"].return_value = "test"
        mocks["get_timezone_name"].return_value = "UTC"
        mocks["get_version_name"].return_value = "Unknown"
        mocks["get_endless_key_uris"].return_value = None
        mocks["get_home_folder"].return_value = self.kolibri_home_tempdir.name

        from kolibri_android.main_activity.activity import MainActivity

        main_activity = MainActivity()

        mocks["configure_webview"].assert_called_once()

        (on_load_fn, on_load_with_usb_fn, on_loading_ready_fn) = mocks[
            "configure_webview"
        ].call_args.args

        on_load_fn()

        # FIXME: We can't use main_activity.run() because it loops forever.

        main_activity.start_kolibri()

        mocks["run"].assert_called_once()
