package org.endlessos.key;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.webkit.WebView;

import androidx.annotation.Nullable;

import com.google.firebase.analytics.FirebaseAnalytics;
import com.google.firebase.crashlytics.FirebaseCrashlytics;

import java.util.Map;

public class KolibriActivity extends Activity {
    private static final String FIREBASE_ENABLED_KEY = "firebase_analytics_collection_enabled";
    private static final String ANALYTICS_SYSPROP = "debug.org.endlessos.key.analytics";

    // Minimum webview major version required
    private static final Map<String, Integer> WEBVIEW_MIN_MAJOR_VERSION =
            Map.of(
                    // Android System Webview
                    "com.google.android.webview", 80);

    // Instance singleton.
    private static KolibriActivity instance;
    private KolibriWebView view;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        Logger.d("Creating activity");
        instance = this;

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
