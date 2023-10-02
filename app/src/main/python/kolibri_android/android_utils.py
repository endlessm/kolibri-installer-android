import logging
import os
import re
from enum import auto
from enum import Enum

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from jnius import autoclass
from jnius import cast
from jnius import java_method
from jnius import JavaException
from jnius import PythonJavaClass

from .runnable import Runnable


logger = logging.getLogger(__name__)

AlertDialogBuilder = autoclass("android.app.AlertDialog$Builder")
AndroidString = autoclass("java.lang.String")
Context = autoclass("android.content.Context")
File = autoclass("java.io.File")
FileProvider = autoclass("androidx.core.content.FileProvider")
Intent = autoclass("android.content.Intent")
Log = autoclass("android.util.Log")
PackageManager = autoclass("android.content.pm.PackageManager")
PythonActivity = autoclass("org.kivy.android.PythonActivity")
Secure = autoclass("android.provider.Settings$Secure")
Timezone = autoclass("java.util.TimeZone")
Uri = autoclass("android.net.Uri")
WebView = autoclass("android.webkit.WebView")

ANDROID_VERSION = autoclass("android.os.Build$VERSION")
SDK_INT = ANDROID_VERSION.SDK_INT

# Minimum webview major version required
WEBVIEW_MIN_MAJOR_VERSION = {
    # Android System Webview
    "com.google.android.webview": 80,
}


# Globals to keep references to Java objects
# See https://github.com/Android-for-Python/Android-for-Python-Users#pyjnius-memory-management
_send_intent = None


def is_service_context():
    return "PYTHON_SERVICE_ARGUMENT" in os.environ


def get_service():
    assert (
        is_service_context()
    ), "Cannot get service, as we are not in a service context."
    PythonService = autoclass("org.kivy.android.PythonService")
    return PythonService.mService


def get_timezone_name():
    return Timezone.getDefault().getDisplayName()


def get_android_node_id():
    return Secure.getString(get_activity().getContentResolver(), Secure.ANDROID_ID)


def get_package_info(package_name="org.endlessos.Key", flags=0):
    return get_activity().getPackageManager().getPackageInfo(package_name, flags)


def get_version_name():
    return get_package_info().versionName


def get_activity():
    if is_service_context():
        return cast("android.app.Service", get_service())
    else:
        return PythonActivity.mActivity


# TODO: check for storage availability, allow user to chose sd card or internal
def get_home_folder():
    kolibri_home_file = get_activity().getExternalFilesDir(None)
    return os.path.join(kolibri_home_file.toString(), "KOLIBRI_DATA")


def get_log_root():
    """Root path for log files"""
    return os.path.join(get_home_folder(), "logs")


def share_by_intent(path=None, filename=None, message=None, app=None, mimetype=None):
    global _send_intent

    assert (
        path or message or filename
    ), "Must provide either a path, a filename, or a msg to share"

    _send_intent = Intent()
    _send_intent.setAction(Intent.ACTION_SEND)
    if path:
        uri = FileProvider.getUriForFile(
            Context.getApplicationContext(),
            "org.endlessos.Key.fileprovider",
            File(path),
        )
        parcelable = cast("android.os.Parcelable", uri)
        _send_intent.putExtra(Intent.EXTRA_STREAM, parcelable)
        _send_intent.setType(AndroidString(mimetype or "*/*"))
        _send_intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    if message:
        if not path:
            _send_intent.setType(AndroidString(mimetype or "text/plain"))
        _send_intent.putExtra(Intent.EXTRA_TEXT, AndroidString(message))
    if app:
        _send_intent.setPackage(AndroidString(app))
    _send_intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    get_activity().startActivity(_send_intent)
    _send_intent = None


def get_signature_key_issuer():
    signature = get_package_info(flags=PackageManager.GET_SIGNATURES).signatures[0]
    cert = x509.load_der_x509_certificate(
        signature.toByteArray().tostring(), default_backend()
    )

    return cert.issuer.rfc4514_string()


def get_signature_key_issuing_organization():
    signer = get_signature_key_issuer()
    orgs = re.findall(r"\bO=([^,]+)", signer)
    return orgs[0] if orgs else ""


class WebViewUpdateClickListener(PythonJavaClass):
    """OnClickListener for webview update dialog"""

    __javainterfaces__ = ["android/content/DialogInterface$OnClickListener"]
    __javacontext__ = "app"

    def __init__(self, activity, package_name):
        super().__init__()
        self.activity = activity
        self.package_name = package_name

    @java_method("(Landroid/content/DialogInterface;I)V")
    def onClick(self, dialog, which):
        logger.debug(f"Starting webview update activity for {self.package_name}")

        # Try both the market:// and https://play.google.com/ URIs.
        uri = Uri.parse(f"market://details?id={self.package_name}")
        intent = Intent(Intent.ACTION_VIEW, uri)
        try:
            self.activity.startActivity(intent)
        except JavaException as err:
            if err.classname != "android.content.ActivityNotFoundException":
                raise

            uri = Uri.parse(
                f"https://play.google.com/store/apps/details?id={self.package_name}"
            )
            intent.setData(uri)
            try:
                self.activity.startActivity(intent)
            except JavaException as err:
                if err.classname != "android.content.ActivityNotFoundException":
                    raise

                logger.warning(
                    f"No activity found to update webview package {self.package_name}"
                )


def check_webview_version():
    """Check if the current webview meets requirements"""
    # getCurrentWebViewPackage is only available since API 26.
    if SDK_INT < 26:
        logger.warning(f"Cannot get webview package on SDK {SDK_INT}")
        return

    pkg = WebView.getCurrentWebViewPackage()
    if pkg is None:
        logger.warning("Could not determine current webview package")
        return

    pkg_name = str(pkg.packageName)
    pkg_version = str(pkg.versionName)
    logger.info(f'Webview package: {pkg_name} "{pkg_version}"')

    min_major_version = WEBVIEW_MIN_MAJOR_VERSION.get(pkg_name)
    if min_major_version is None:
        logger.warning(f"Cannot check webview version for {pkg_name}")
        return

    try:
        major_version = int(pkg_version.split(".", 1)[0])
    except ValueError:
        logger.warning(f'Could not parse webview major version from "{pkg_version}"')
        return

    logger.debug(f"{pkg_name} major version: {major_version}")
    if major_version >= min_major_version:
        return

    # Create a dialog to instruct the user to update the webview.
    logger.debug(f"Initiating webview package {pkg_name} update")
    activity = get_activity()
    builder = AlertDialogBuilder(activity)
    builder.setMessage(
        AndroidString(
            "You need to update the Android System Webview component to use Endless Key."
        )
    )
    builder.setPositiveButton(
        AndroidString("Update"), WebViewUpdateClickListener(activity, pkg_name)
    )
    builder.setCancelable(False)

    # Show the dialog on the UI thread.
    Runnable(builder.show)()


class StartupState(Enum):
    FIRST_TIME = auto()
    NETWORK_USER = auto()

    @classmethod
    def get_current_state(cls):
        """
        Returns the current app startup state that could be:
            * FIRST_TIME
            * NETWORK_USER
        """
        home = get_home_folder()

        # if there's no database in the home folder this is the first launch
        db_path = os.path.join(home, "db.sqlite3")
        if not os.path.exists(db_path):
            return cls.FIRST_TIME

        # in other case, the app is initialized but with content downloaded
        # using the network
        return cls.NETWORK_USER


class AndroidLogHandler(logging.Handler):
    """Logging handler dispatching to android.util.Log

    Converts Python logging records to Android log messages viewable
    with "adb logcat". The handler converts logging levels to log
    priorities, which allows filtering by priority with logcat or other
    Android log analysis tools.
    """

    def __init__(self, tag=None):
        super().__init__()

        self.tag = tag or get_activity().getPackageName()

    def emit(self, record):
        try:
            msg = self.format(record)
            priority = self.level_to_priority(record.levelno)
            Log.println(priority, self.tag, msg)
        except:  # noqa: E722
            self.handleError(record)

    @staticmethod
    def level_to_priority(level):
        if level >= logging.CRITICAL:
            return Log.ASSERT
        elif level >= logging.ERROR:
            return Log.ERROR
        elif level >= logging.WARNING:
            return Log.WARN
        elif level >= logging.INFO:
            return Log.INFO
        elif level >= logging.DEBUG:
            return Log.DEBUG
        else:
            return Log.VERBOSE


def get_logging_config(LOG_ROOT, debug=False, debug_database=False):
    """Logging configuration

    This is customized from
    kolibri.utils.logger.get_default_logging_config(), which is the
    basis for the logging configuration used in Kolibri.
    """
    # This is the general level
    DEFAULT_LEVEL = "INFO" if not debug else "DEBUG"
    DATABASE_LEVEL = "INFO" if not debug_database else "DEBUG"
    DEFAULT_HANDLERS = ["android", "file"]

    return {
        "version": 1,
        "disable_existing_loggers": False,
        # No filters are used here, but kolibri adds some and expects
        # the top level filters dict to exist.
        "filters": {},
        "formatters": {
            "simple": {
                "format": "%(name)s: %(message)s",
            },
            "full": {
                "format": "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "android": {
                "class": "kolibri_android.android_utils.AndroidLogHandler",
                # Since Android loggingthat already has timestamps and
                # priority levels, they aren't needed here.
                "formatter": "simple",
            },
            "file": {
                # Kolibri uses a customized version of
                # logging.handlers.TimedRotatingFileHandler. We don't
                # want to use that here to avoid importing kolibri too
                # early. IMO, the regular rotating handler based on size
                # is better in the Android case so the total disk space
                # used for logs is managed.
                "class": "logging.handlers.RotatingFileHandler",
                "filename": os.path.join(LOG_ROOT, "kolibri.txt"),
                "maxBytes": 5 << 20,  # 5 Mib
                "backupCount": 5,
                "formatter": "full",
            },
        },
        "loggers": {
            "": {
                "handlers": DEFAULT_HANDLERS,
                "level": DEFAULT_LEVEL,
            },
            "kolibri_android": {
                # Always log our code at debug level.
                "level": "DEBUG",
            },
            "jnius": {
                # jnius debug logs are very noisy, so limit it to info.
                "level": "INFO",
            },
            "kolibri": {
                # kolibri expects the handlers list to exist so it can
                # append django's email handler.
                "handlers": [],
            },
            # For now, we do not fetch debugging output from this
            # We should introduce custom debug log levels or log
            # targets, i.e. --debug-level=high
            "kolibri.core.tasks.worker": {
                "level": "INFO",
            },
            "django": {
                # kolibri expects the handlers list to exist so it can
                # append django's email handler.
                "handlers": [],
            },
            "django.db.backends": {
                "level": DATABASE_LEVEL,
            },
            "django.request": {
                # kolibri expects the handlers list to exist so it can
                # append django's email handler.
                "handlers": [],
            },
            "django.template": {
                # Django template debug is very noisy, only log INFO and above.
                "level": "INFO",
            },
        },
    }
