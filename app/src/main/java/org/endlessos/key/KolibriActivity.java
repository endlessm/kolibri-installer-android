package org.endlessos.key;

import android.app.Activity;
import android.os.Bundle;

import androidx.annotation.Nullable;

public class KolibriActivity extends Activity {
    // Instance singleton.
    private static KolibriActivity instance;
    private KolibriWebView view;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        Logger.d("Creating activity");
        instance = this;

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
}
