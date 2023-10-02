package org.endlessos.key;

import android.app.Activity;
import android.os.Bundle;

import androidx.annotation.Nullable;

import com.google.firebase.analytics.FirebaseAnalytics;
import com.google.firebase.crashlytics.FirebaseCrashlytics;

public class KolibriActivity extends Activity {
    private static final String FIREBASE_ENABLED_KEY = "firebase_analytics_collection_enabled";
    private static final String ANALYTICS_SYSPROP = "debug.org.endlessos.key.analytics";

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
}
