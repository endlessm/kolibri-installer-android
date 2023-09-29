package org.endlessos.key;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.net.Uri;
import android.util.Log;
import android.view.View;
import android.webkit.ConsoleMessage;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;

public class KolibriWebView extends WebView {
    private static final String WEB_CONSOLE_TAG = "EKWebConsole";

    public KolibriWebView(Activity activity) {
        super(activity);
        addSettings();
        setWebViewClient(new KolibriWebViewClient(activity));
        setWebChromeClient(new KolibriWebChromeClient(activity));
    }

    @SuppressLint("SetJavaScriptEnabled")
    @SuppressWarnings("deprecation")
    private void addSettings() {
        WebSettings settings = getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        // These are needed to allow opening the loadingScreen from
        // file:///android_asset but are deprecated in API 30.
        settings.setAllowFileAccessFromFileURLs(true);
        settings.setAllowUniversalAccessFromFileURLs(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        // Use a desktop-like user agent to appease the Unity web loader.
        settings.setUserAgentString(
                settings.getUserAgentString()
                        .replace("Android", "Human")
                        .replaceFirst("Version\\/\\d+\\.\\d+", ""));
    }

    private class KolibriWebViewClient extends WebViewClient {
        private Context context;

        public KolibriWebViewClient(Context context) {
            super();
            this.context = context;
        }

        @Override
        public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
            // Load local URLs in this view.
            final Uri url = request.getUrl();
            if (url.getScheme().equals("file") || url.getHost().equals("127.0.0.1")) {
                return false;
            }

            // Otherwise open in an external browser and tell this view to stop loading it.
            context.startActivity(new Intent(Intent.ACTION_VIEW, url));
            return true;
        }
    }

    // Configure the WebView to allow fullscreen based on:
    // https://stackoverflow.com/questions/15768837/playing-html5-video-on-fullscreen-in-android-webview/56186877#56186877
    private class KolibriWebChromeClient extends WebChromeClient {
        private Activity mActivity;
        private View mCustomView;
        private WebChromeClient.CustomViewCallback mCustomViewCallback;
        private int mOriginalOrientation;
        private int mOriginalSystemUiVisibility;

        KolibriWebChromeClient(Activity activity) {
            super();
            mActivity = activity;
        }

        @Override
        public Bitmap getDefaultVideoPoster() {
            if (mCustomView == null) {
                return null;
            }
            return BitmapFactory.decodeResource(
                    mActivity.getApplicationContext().getResources(), 2130837573);
        }

        @Override
        @SuppressWarnings("deprecation")
        public void onHideCustomView() {
            ((FrameLayout) mActivity.getWindow().getDecorView()).removeView(this.mCustomView);
            this.mCustomView = null;
            mActivity
                    .getWindow()
                    .getDecorView()
                    .setSystemUiVisibility(this.mOriginalSystemUiVisibility);
            mActivity.setRequestedOrientation(this.mOriginalOrientation);
            this.mCustomViewCallback.onCustomViewHidden();
            this.mCustomViewCallback = null;
        }

        @Override
        @SuppressWarnings("deprecation")
        public void onShowCustomView(
                View paramView, WebChromeClient.CustomViewCallback paramCustomViewCallback) {
            if (this.mCustomView != null) {
                onHideCustomView();
                return;
            }
            this.mCustomView = paramView;
            this.mOriginalSystemUiVisibility =
                    mActivity.getWindow().getDecorView().getSystemUiVisibility();
            this.mOriginalOrientation = mActivity.getRequestedOrientation();
            this.mCustomViewCallback = paramCustomViewCallback;
            ((FrameLayout) mActivity.getWindow().getDecorView())
                    .addView(this.mCustomView, new FrameLayout.LayoutParams(-1, -1));
            mActivity
                    .getWindow()
                    .getDecorView()
                    .setSystemUiVisibility(3846 | View.SYSTEM_UI_FLAG_LAYOUT_STABLE);
        }

        @Override
        public boolean onConsoleMessage(ConsoleMessage consoleMessage) {
            String logMessage =
                    consoleMessage.message() + " -- Source: " + consoleMessage.sourceId();
            if (consoleMessage.messageLevel() == ConsoleMessage.MessageLevel.ERROR) {
                Log.e(WEB_CONSOLE_TAG, logMessage);
            } else {
                Log.v(WEB_CONSOLE_TAG, logMessage);
            }
            return true;
        }
    }
}
