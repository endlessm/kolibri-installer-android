import json
import logging
import os
import re
from enum import auto
from enum import Enum
from pathlib import Path
from urllib.parse import parse_qsl
from urllib.parse import urlparse

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from jnius import autoclass
from jnius import cast
from jnius import java_method
from jnius import JavaException
from jnius import jnius
from jnius import PythonJavaClass

from .referrer import get_referrer_details
from .runnable import Runnable


logger = logging.getLogger(__name__)

Activity = autoclass("android.app.Activity")
AlertDialogBuilder = autoclass("android.app.AlertDialog$Builder")
AndroidString = autoclass("java.lang.String")
BuildConfig = autoclass("org.endlessos.Key.BuildConfig")
Context = autoclass("android.content.Context")
Environment = autoclass("android.os.Environment")
File = autoclass("java.io.File")
FileProvider = autoclass("androidx.core.content.FileProvider")
FirebaseAnalytics = autoclass("com.google.firebase.analytics.FirebaseAnalytics")
FirebaseCrashlytics = autoclass("com.google.firebase.crashlytics.FirebaseCrashlytics")
Intent = autoclass("android.content.Intent")
Log = autoclass("android.util.Log")
NotificationBuilder = autoclass("android.app.Notification$Builder")
NotificationManager = autoclass("android.app.NotificationManager")
PackageManager = autoclass("android.content.pm.PackageManager")
PendingIntent = autoclass("android.app.PendingIntent")
PythonActivity = autoclass("org.kivy.android.PythonActivity")
Secure = autoclass("android.provider.Settings$Secure")
SystemProperties = autoclass("android.os.SystemProperties")
Timezone = autoclass("java.util.TimeZone")
Toast = autoclass("android.widget.Toast")
Uri = autoclass("android.net.Uri")
WebView = autoclass("android.webkit.WebView")
FirebaseApp = autoclass("com.google.firebase.FirebaseApp")

ANDROID_VERSION = autoclass("android.os.Build$VERSION")
RELEASE = ANDROID_VERSION.RELEASE
SDK_INT = ANDROID_VERSION.SDK_INT

# Chrome OS constant UUID for the My Files volume. In Android this shows
# up as a removable volume, which throws off the detection of USB
# devices. Below it's filtered out from removable storage searches.
#
# https://source.chromium.org/chromium/chromium/src/+/main:ash/components/arc/volume_mounter/arc_volume_mounter_bridge.cc;l=51
MY_FILES_UUID = "0000000000000000000000000000CAFEF00D2019"

# System property configuring Analytics and Crashlytics.
ANALYTICS_SYSPROP = "debug.org.endlessos.key.analytics"


USB_CONTENT_FLAG_FILENAME = "usb_content_flag"

# Minimum webview major version required
WEBVIEW_MIN_MAJOR_VERSION = {
    # Android System Webview
    "com.google.android.webview": 80,
}


# Globals to keep references to Java objects
# See https://github.com/Android-for-Python/Android-for-Python-Users#pyjnius-memory-management
_notification_builder = None
_notification_intent = None
_send_intent = None

# Path.is_relative_to only on python 3.9+.
if not hasattr(Path, "is_relative_to"):

    def _path_is_relative_to(self, *other):
        try:
            self.relative_to(*other)
            return True
        except ValueError:
            return False

    Path.is_relative_to = _path_is_relative_to


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


def start_service(service_name, service_args=None):
    service_args = service_args or {}
    service = autoclass("org.endlessos.Key.Service{}".format(service_name.title()))
    service.start(PythonActivity.mActivity, json.dumps(dict(service_args)))


def get_service_args():
    assert (
        is_service_context()
    ), "Cannot get service args, as we are not in a service context."
    return json.loads(os.environ.get("PYTHON_SERVICE_ARGUMENT") or "{}")


def get_package_info(package_name="org.endlessos.Key", flags=0):
    return get_activity().getPackageManager().getPackageInfo(package_name, flags)


def get_version_name():
    return get_package_info().versionName


def get_activity():
    if is_service_context():
        return cast("android.app.Service", get_service())
    else:
        return PythonActivity.mActivity


def get_preferences():
    activity = get_activity()
    return activity.getSharedPreferences(
        activity.getPackageName(), Activity.MODE_PRIVATE
    )


def is_app_installed(app_id):

    manager = get_activity().getPackageManager()

    try:
        manager.getPackageInfo(app_id, PackageManager.GET_ACTIVITIES)
    except jnius.JavaException:
        return False

    return True


# TODO: check for storage availability, allow user to chose sd card or internal
def get_home_folder():
    kolibri_home_file = get_activity().getExternalFilesDir(None)
    return os.path.join(kolibri_home_file.toString(), "KOLIBRI_DATA")


def get_log_root():
    """Root path for log files"""
    return os.path.join(get_home_folder(), "logs")


def show_toast(context, msg, duration):
    """Helper to create and show a Toast message"""

    def func():
        Toast.makeText(context, AndroidString(msg), duration).show()

    runnable = Runnable(func)
    runnable()


def send_whatsapp_message(msg):
    share_by_intent(message=msg, app="com.whatsapp")


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


def init_firebase_app():
    app_context = get_service().getApplication().getApplicationContext()
    FirebaseApp.initializeApp(app_context)


def make_service_foreground(title, message):
    global _notification_builder
    global _notification_intent

    service = get_service()
    Drawable = autoclass("{}.R$drawable".format(service.getPackageName()))
    app_context = service.getApplication().getApplicationContext()

    if SDK_INT >= 26:
        NotificationChannel = autoclass("android.app.NotificationChannel")
        notification_service = cast(
            NotificationManager,
            get_activity().getSystemService(Context.NOTIFICATION_SERVICE),
        )
        channel_id = get_activity().getPackageName()
        app_channel = NotificationChannel(
            channel_id,
            "Kolibri Background Server",
            NotificationManager.IMPORTANCE_DEFAULT,
        )
        notification_service.createNotificationChannel(app_channel)
        _notification_builder = NotificationBuilder(app_context, channel_id)
    else:
        _notification_builder = NotificationBuilder(app_context)

    _notification_builder.setContentTitle(AndroidString(title))
    _notification_builder.setContentText(AndroidString(message))
    _notification_intent = Intent(app_context, PythonActivity)
    _notification_intent.setFlags(
        Intent.FLAG_ACTIVITY_CLEAR_TOP
        | Intent.FLAG_ACTIVITY_SINGLE_TOP
        | Intent.FLAG_ACTIVITY_NEW_TASK
    )
    _notification_intent.setAction(Intent.ACTION_MAIN)
    _notification_intent.addCategory(Intent.CATEGORY_LAUNCHER)
    intent = PendingIntent.getActivity(service, 0, _notification_intent, 0)
    _notification_builder.setContentIntent(intent)
    _notification_builder.setSmallIcon(Drawable.icon)
    _notification_builder.setAutoCancel(True)
    new_notification = _notification_builder.getNotification()
    service.startForeground(1, new_notification)
    _notification_builder = None
    _notification_intent = None


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


def is_external_app_path(path):
    path = Path(path).resolve()
    activity = get_activity()

    for app_dir in activity.getExternalFilesDirs(None):
        if app_dir is None or not Environment.isExternalStorageRemovable(app_dir):
            continue
        if path.is_relative_to(Path(app_dir.toString())):
            return True
    return False


def _android11_ext_storage_workarounds():
    """Workarounds for Android 11 external storage bugs

    See https://issuetracker.google.com/issues/232290073 for details.
    """
    if RELEASE != "11":
        return

    from os import access as _os_access
    from os import listdir as _os_listdir

    logger.info("Applying Android 11 workarounds")

    def access(path, mode, *, dir_fd=None, effective_ids=False, follow_symlinks=True):
        can_access = _os_access(
            path,
            mode,
            dir_fd=dir_fd,
            effective_ids=effective_ids,
            follow_symlinks=follow_symlinks,
        )

        # Workaround a bug on Android 11 where access with W_OK on an
        # external app private directory returns EACCESS even though
        # those directories are obviously writable for the app.
        if (
            not can_access
            # If dir_fd is set, we can't determine the full path.
            and dir_fd is None
            # Both effective_ids and follow_symlinks use faccessat. For
            # now don't bother handling those.
            and not effective_ids
            and follow_symlinks
            # Finally, match on a writable test for an external directory.
            and mode & os.W_OK
            and os.path.isdir(path)
            and is_external_app_path(path)
        ):
            logger.warning(
                "Forcing os.access to True for writable test on external app directory %s",
                path,
            )
            can_access = True

        return can_access

    def listdir(path=None):
        try:
            return _os_listdir(path)
        except PermissionError as err:
            # If given a path (not an open directory fd) in external app
            # storage, ignore PermissionError and return an empty list
            # to workaround an Android bug where opendir returns
            # EACCESS. The empty list is not useful, but it's better
            # than failing in a case that shouldn't.
            if path is None:
                path = "."
            if isinstance(path, (str, bytes, os.PathLike)) and is_external_app_path(
                path
            ):
                logger.warning(
                    "Ignoring os.listdir error %s on external app directory",
                    err,
                )
                return []

            raise

    os.access = access
    os.listdir = listdir


def apply_android_workarounds():
    _android11_ext_storage_workarounds()


def get_referrer_url(context):
    """Get Google Play referrer URL

    Retrieves the referrer_url value from shared preferences. If that's
    not set, the URL is queried from the Play Store and stored.
    """
    preferences = get_preferences()
    url = preferences.getString("referrer_url", None)
    if url is None:
        details = get_referrer_details(context)
        if details is not None:
            url = details.getInstallReferrer()
            logger.debug(f"Setting referrer_url='{url}'")
            editor = get_preferences().edit()
            editor.putString("referrer_url", url)
            editor.commit()

    logger.info(f"Installed from referrer URL '{url}'")
    return url


def get_referrer_params(context):
    """Get Google Play referrer UTM parameters"""
    # A full Google Play URL looks has the UTM parameters URL encoded
    # within the referrer query parameter. However, it appears that the
    # Install Referrer API often (always?) returns only the referrer
    # value URL decoded. Try to handle both possibilities.
    url = get_referrer_url(context)
    url_parts = urlparse(url)
    if url_parts.scheme:
        # Full URL. Try to get the referrer query parameter value.
        url_params = dict(parse_qsl(url_parts.query))
        referrer = url_params.get("referrer", "")
    else:
        # Assume the URL is just the referrer value.
        referrer = url

    return dict(parse_qsl(referrer))


def setup_analytics():
    """Enable or disable Firebase Analytics and Crashlytics

    For release builds, they're enabled by default. For debug builds,
    they're disabled by default. They can be explicitly enabled or
    disabled using the debug.org.endlessos.key.analytics system
    property. For example, `adb shell setprop
    debug.org.endlessos.key.analytics true`.
    """
    context = get_activity()
    referrer = get_referrer_params(context)
    logger.debug(f"Install referrer parameters: {referrer}")

    if BuildConfig.DEBUG:
        logger.debug("Debug build, analytics default disabled")
        analytics_default = False
    else:
        logger.debug("Release build, analytics default enabled")
        analytics_default = True

    # Allow explicitly enabling or disabling using a system property.
    analytics_enabled = SystemProperties.getBoolean(
        ANALYTICS_SYSPROP,
        analytics_default,
    )
    if analytics_enabled is not analytics_default:
        logger.debug(
            "Analytics %s from %s system property",
            "enabled" if analytics_enabled else "disabled",
            ANALYTICS_SYSPROP,
        )

    # Analytics and Crashlytics collection enablement persists across
    # executions, so actively enable or disable based on the current
    # settings.
    logging.info(
        "%s Firebase Analytics and Crashlytics",
        "Enabling" if analytics_enabled else "Disabling",
    )
    analytics = FirebaseAnalytics.getInstance(context)
    crashlytics = FirebaseCrashlytics.getInstance()
    analytics.setAnalyticsCollectionEnabled(analytics_enabled)
    crashlytics.setCrashlyticsCollectionEnabled(analytics_enabled)


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
