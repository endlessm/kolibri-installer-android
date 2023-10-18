package org.endlessos.key;

import android.app.Service;
import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.Message;
import android.os.Messenger;
import android.os.RemoteException;

import androidx.annotation.Nullable;

import com.chaquo.python.PyObject;
import com.chaquo.python.Python;

import java.io.IOException;

public class KolibriService extends Service {
    // Message IDs.
    static final int MSG_GET_SERVER_DATA = 1;

    // Singleton instance.
    private static KolibriService instance;
    private PyObject serverBus;
    private String serverUrl;
    private String appKey;

    @Override
    public IBinder onBind(Intent intent) {
        return messenger.getBinder();
    }

    @Override
    public void onCreate() {
        instance = this;

        try {
            KolibriUtils.initializeKolibri(this);
        } catch (IOException e) {
            Logger.e("Failed to setup Kolibri", e);
            return;
        }

        if (serverBus == null) {
            final Python python = Python.getInstance();
            final PyObject serverModule = python.getModule("kolibri_android.server");
            serverBus = serverModule.callAttr("ServerProcessBus");
        }

        Logger.i("Starting Kolibri server");
        serverBus.callAttr("start");
        serverUrl = serverBus.callAttr("get_url").toString();
        appKey = serverBus.callAttr("get_app_key").toString();
        Logger.d("Server started on " + serverUrl);
    }

    @Override
    public void onDestroy() {
        Logger.i("Stopping Kolibri server");
        serverBus.callAttr("stop");
        Logger.d("Server stopped");
        serverUrl = null;
        appKey = null;
        instance = null;
    }

    /**
     * Returns the current KolibriService instance.
     *
     * @return The instance or <code>null</code> if it hasn't been created.
     */
    @Nullable
    public static KolibriService getInstance() {
        return instance;
    }

    /**
     * Returns the current Kolibri server URL.
     *
     * @return The URL or <code>null</code> if it hasn't been created.
     */
    @Nullable
    public String getServerUrl() {
        return serverUrl;
    }

    /**
     * Returns the current Kolibri app key.
     *
     * @return The key or <code>null</code> if it hasn't been created.
     */
    @Nullable
    public String getAppKey() {
        return appKey;
    }

    // Messenger and handler for receiving messages.
    private Messenger messenger = new Messenger(new KolibriHandler(Looper.getMainLooper()));

    private class KolibriHandler extends Handler {
        public KolibriHandler(Looper looper) {
            super(looper);
        }

        @Override
        public void handleMessage(Message msg) {
            switch (msg.what) {
                case MSG_GET_SERVER_DATA:
                    // Ensure the replyTo messenger has been set.
                    if (msg.replyTo == null) {
                        Logger.e("replyTo not set in GET_SERVER_DATA message");
                        return;
                    }

                    // Send the server data back to the replyTo messenger with the ID specified as
                    // an argument.
                    final Bundle data = new Bundle();
                    data.putString("serverUrl", serverUrl);
                    data.putString("appKey", appKey);
                    final Message reply = Message.obtain(null, msg.arg1);
                    reply.setData(data);
                    try {
                        msg.replyTo.send(reply);
                    } catch (RemoteException e) {
                        Logger.e("Failed to send message", e);
                    }
                    break;
                default:
                    super.handleMessage(msg);
            }
        }
    }
}
