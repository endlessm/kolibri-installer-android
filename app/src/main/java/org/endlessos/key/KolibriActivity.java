package org.endlessos.key;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.ComponentName;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.ServiceConnection;
import android.content.pm.PackageInfo;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.Message;
import android.os.Messenger;
import android.os.RemoteException;
import android.webkit.CookieManager;
import android.webkit.WebView;

import androidx.annotation.Nullable;

import com.google.firebase.analytics.FirebaseAnalytics;
import com.google.firebase.crashlytics.FirebaseCrashlytics;

import java.util.Map;

public class KolibriActivity extends Activity {
    private static final String FIREBASE_ENABLED_KEY = "firebase_analytics_collection_enabled";
    private static final String ANALYTICS_SYSPROP = "debug.org.endlessos.key.analytics";

    // Message IDs.
    static final int MSG_SET_SERVER_DATA = 1;

    // Instance state keys.
    private static final String STATE_LAST_URL_PATH = "lastUrlPath";

    // Minimum webview major version required
    private static final Map<String, Integer> WEBVIEW_MIN_MAJOR_VERSION =
            Map.of(
                    // Android System Webview
                    "com.google.android.webview", 80);

    // Instance singleton.
    private static KolibriActivity instance;
    private KolibriWebView view;
    private String lastUrlPath = "/";
    private boolean kolibriBound = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        Logger.d("Creating activity");
        instance = this;

        if (savedInstanceState != null) {
            lastUrlPath = savedInstanceState.getString(STATE_LAST_URL_PATH, "/");
            Logger.d("Restored last URL path " + lastUrlPath);
        }

        // Setup analytics and crashlytics.
        setupAnalytics();

        // Check the webview version.
        checkWebViewVersion();

        // Create the webview and open the loading screen.
        view = new KolibriWebView(this);
        setContentView(view);
        view.loadUrl("file:///android_asset/loadingScreen/index.html");
    }

    @Override
    protected void onStart() {
        super.onStart();
        Logger.d("Starting activity");

        final Intent kolibriIntent = new Intent(this, KolibriService.class);
        Logger.i("Binding Kolibri service");
        if (!bindService(kolibriIntent, kolibriConnection, Context.BIND_AUTO_CREATE)) {
            Logger.e("Could not bind to Kolibri service");
        }
    }

    @Override
    protected void onStop() {
        super.onStop();
        Logger.d("Stopping activity");

        setLastUrlPathFromCurrentUrl();
        view.loadUrl("about:blank");

        Logger.i("Unbinding Kolibri service");
        unbindService(kolibriConnection);
        kolibriBound = true;
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        Logger.d("Destroying activity");
        instance = null;
    }

    /**
     * Returns the current KolibriActivity instance.
     *
     * @return The instance or <code>null</code> if it hasn't been created.
     */
    @Nullable
    public static KolibriActivity getInstance() {
        return instance;
    }

    private void setAppKeyCookie(Uri serverUrl, String appKey) {
        CookieManager.getInstance().setCookie(serverUrl.toString(), "app_key_cookie=" + appKey);
    }

    private void setLastUrlPathFromCurrentUrl() {
        final String viewUrl = view.getUrl();
        if (viewUrl == null) {
            return;
        }
        final Uri url = Uri.parse(viewUrl);
        final String path = url.getPath();
        if (path == null) {
            Logger.w("Could not determine path in URL " + url);
            return;
        }
        final String fragment = url.getFragment();
        lastUrlPath = path + ((fragment != null) ? "#" + fragment : "");
        Logger.i("Set last URL path to " + lastUrlPath);
    }

    private void updateServerUrl(Uri serverUrl) {
        final String url =
                String.format(
                        "%s://%s%s", serverUrl.getScheme(), serverUrl.getAuthority(), lastUrlPath);
        runOnUiThread(
                new Runnable() {
                    @Override
                    public void run() {
                        Logger.i("Loading last URL " + url);
                        view.loadUrl(url);
                    }
                });
    }

    // Messenger and handler for receiving messages.
    private Messenger messenger = new Messenger(new ActivityHandler(Looper.getMainLooper()));

    private class ActivityHandler extends Handler {
        public ActivityHandler(Looper looper) {
            super(looper);
        }

        @Override
        public void handleMessage(Message msg) {
            switch (msg.what) {
                case MSG_SET_SERVER_DATA:
                    handleSetServerDataMessage(msg);
                    break;
                default:
                    super.handleMessage(msg);
            }
        }

        private void handleSetServerDataMessage(Message msg) {
            // If the kolibri service is being unbound or already disconnected, don't bother doing
            // anything with the received message.
            if (!kolibriBound) {
                Logger.d("Ignoring SET_SERVER_DATA message since Kolibri service is being unbound");
                return;
            }

            final Bundle data = msg.getData();
            if (data == null) {
                Logger.e("Received reply with no data");
                return;
            }

            final String url = data.getString("serverUrl");
            if (url == null) {
                Logger.e("Received null server URL");
                return;
            }
            final Uri serverUrl = Uri.parse(url);

            final String appKey = data.getString("appKey");
            if (appKey == null) {
                Logger.e("Received null app key");
                return;
            }

            setAppKeyCookie(serverUrl, appKey);
            updateServerUrl(serverUrl);
        }
    }

    // KolibriService connection
    private ServiceConnection kolibriConnection =
            new ServiceConnection() {
                @Override
                public void onServiceConnected(ComponentName name, IBinder ibinder) {
                    Logger.d("Kolibri service connected");
                    kolibriBound = true;

                    // Send a message to the service to get the server data with the activity's
                    // messenger and ID to reply to.
                    final Messenger service = new Messenger(ibinder);
                    final Message msg =
                            Message.obtain(
                                    null,
                                    KolibriService.MSG_GET_SERVER_DATA,
                                    MSG_SET_SERVER_DATA,
                                    0);
                    msg.replyTo = messenger;
                    try {
                        service.send(msg);
                    } catch (RemoteException e) {
                        Logger.e("Failed to send message", e);
                    }
                }

                @Override
                public void onServiceDisconnected(ComponentName name) {
                    Logger.d("Kolibri service disconnected");
                    kolibriBound = false;
                }
            };

    private void setupAnalytics() {
        // Use the value from the manifest as the default with a fallback as enabled for release
        // builds and disabled for debug builds.
        final Bundle metadata = KolibriUtils.getAppMetaData(this);
        boolean analyticsDefault = !BuildConfig.DEBUG;
        if (metadata != null) {
            analyticsDefault = metadata.getBoolean(FIREBASE_ENABLED_KEY, analyticsDefault);
        }
        Logger.d("Analytics " + (analyticsDefault ? "enabled" : "disabled") + " by default");

        // Allow overriding with the system property.
        final boolean analyticsEnabled =
                KolibriUtils.getSysPropBoolean(ANALYTICS_SYSPROP, analyticsDefault);
        if (analyticsEnabled != analyticsDefault) {
            Logger.d(
                    "Analytics "
                            + (analyticsEnabled ? "enabled" : "disabled")
                            + " from "
                            + ANALYTICS_SYSPROP
                            + " system property");
        }

        // Analytics and Crashlytics collection enablement persists across executions, so actively
        // enable or disable based on the current settings.
        Logger.i(
                (analyticsEnabled ? "Enabling" : "Disabling")
                        + " Firebase Analytics and Crashlytics");
        FirebaseAnalytics.getInstance(this).setAnalyticsCollectionEnabled(analyticsEnabled);
        FirebaseCrashlytics.getInstance().setCrashlyticsCollectionEnabled(analyticsEnabled);
    }

    /** Check if the current webview meets requirements */
    private void checkWebViewVersion() {
        // getCurrentWebViewPackage is only available since API 26.
        if (Build.VERSION.SDK_INT < 26) {
            Logger.w("Cannot get webview package on SDK " + Build.VERSION.SDK_INT);
            return;
        }

        final PackageInfo pkg = WebView.getCurrentWebViewPackage();
        if (pkg == null) {
            Logger.w("Could not determine current webview package");
            return;
        }

        Logger.i(String.format("Webview package: %s \"%s\"", pkg.packageName, pkg.versionName));

        final int minMajorVersion = WEBVIEW_MIN_MAJOR_VERSION.getOrDefault(pkg.packageName, -1);
        if (minMajorVersion < 0) {
            Logger.w("Cannot check webview version for " + pkg.packageName);
            return;
        }

        final int majorVersion;
        try {
            majorVersion = Integer.parseInt(pkg.versionName.split("\\.")[0]);
        } catch (NumberFormatException e) {
            Logger.w(
                    String.format(
                            "Could not parse webview major version from \"%s\"", pkg.versionName),
                    e);
            return;
        }

        Logger.d(pkg.packageName + " major version: " + majorVersion);
        if (majorVersion >= minMajorVersion) {
            return;
        }

        // Create a dialog to instruct the user to update the webview.
        Logger.d("Initiating webview package " + pkg.packageName + " update");
        DialogInterface.OnClickListener listener =
                new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface dialog, int which) {
                        Logger.d("Starting webview update activity for " + pkg.packageName);
                        // Try both the market:// and https://play.google.com/ URIs.
                        Uri uri = Uri.parse("market://details?id=" + pkg.packageName);
                        final Intent intent = new Intent(Intent.ACTION_VIEW, uri);
                        try {
                            startActivity(intent);
                        } catch (ActivityNotFoundException e1) {
                            uri =
                                    Uri.parse(
                                            "https://play.google.com/store/apps/details?id="
                                                    + pkg.packageName);
                            intent.setData(uri);
                            try {
                                startActivity(intent);
                            } catch (ActivityNotFoundException e2) {
                                Logger.w(
                                        "No activity found to update webview package "
                                                + pkg.packageName);
                            }
                        }
                    }
                };
        AlertDialog dialog =
                new AlertDialog.Builder(this)
                        .setMessage(R.string.webview_check_message)
                        .setPositiveButton(R.string.webview_check_update, listener)
                        .setCancelable(false)
                        .create();

        runOnUiThread(
                new Runnable() {
                    @Override
                    public void run() {
                        dialog.show();
                    }
                });
    }
}
