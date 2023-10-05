package org.endlessos.key;

import static org.junit.Assert.assertNotEquals;
import static org.junit.Assert.assertNotNull;

import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.os.Bundle;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.Message;
import android.os.Messenger;
import android.os.RemoteException;
import android.util.Log;

import androidx.test.core.app.ApplicationProvider;
import androidx.test.rule.ServiceTestRule;

import org.junit.Rule;
import org.junit.Test;

import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

public class KolibriServiceTest {
    private static final String TAG = "KolibriServiceTest";

    // The service can be slow to start, so extend the default bind timeout from 5 seconds.
    @Rule
    public final ServiceTestRule mServiceRule = ServiceTestRule.withTimeout(60, TimeUnit.SECONDS);

    @Test
    public void testBindService() throws TimeoutException {
        Context context = ApplicationProvider.getApplicationContext();
        Intent intent = new Intent(context, KolibriService.class);
        IBinder binder = mServiceRule.bindService(intent);
        assertNotNull(binder);
    }

    @Test
    public void testGetServerData() throws InterruptedException, RemoteException, TimeoutException {
        final Context context = ApplicationProvider.getApplicationContext();
        final Intent intent = new Intent(context, KolibriService.class);
        final TestConnection connection = new TestConnection();
        final IBinder binder =
                mServiceRule.bindService(intent, connection, Context.BIND_AUTO_CREATE);
        assertNotNull(binder);

        // First send the message without the replyTo messenger. This just ensures the service
        // handles invalid arguments.
        final Message msg = Message.obtain(null, KolibriService.MSG_GET_SERVER_DATA);
        connection.service.send(msg);

        // Construct a messenger to receive the response.
        final ArrayBlockingQueue<Bundle> queue = new ArrayBlockingQueue<Bundle>(1);
        final Messenger messenger = new Messenger(new TestHandler(Looper.getMainLooper(), queue));

        // Send the message with the proper arguments and validate the reply.
        msg.arg1 = TestHandler.MSG_SET_SERVER_DATA;
        msg.replyTo = messenger;
        connection.service.send(msg);
        final Bundle data = queue.poll(5, TimeUnit.SECONDS);
        assertNotNull("Service did not send GET_SERVER_DATA reply", data);

        final String url = data.getString("serverUrl");
        assertNotNull("Reply data does not contain serverUrl", url);
        assertNotEquals("Reply serverUrl is empty", "", url);

        final String appKey = data.getString("appKey");
        assertNotNull("Reply data does not contain appKey", appKey);
        assertNotEquals("Reply appKey is empty", "", appKey);
    }

    private class TestConnection implements ServiceConnection {
        public Messenger service;

        @Override
        public void onServiceConnected(ComponentName name, IBinder ibinder) {
            Log.d(TAG, "Service connected");
            service = new Messenger(ibinder);
        }

        @Override
        public void onServiceDisconnected(ComponentName name) {
            Log.d(TAG, "Service disconnected");
            service = null;
        }
    }

    private class TestHandler extends Handler {
        static final int MSG_SET_SERVER_DATA = 1;

        private ArrayBlockingQueue<Bundle> queue;

        public TestHandler(Looper looper, ArrayBlockingQueue<Bundle> queue) {
            super(looper);
            this.queue = queue;
        }

        @Override
        public void handleMessage(Message msg) {
            Log.d(TAG, "Received message: " + msg);
            switch (msg.what) {
                case MSG_SET_SERVER_DATA:
                    queue.add(msg.getData());
                    break;
                default:
                    super.handleMessage(msg);
            }
        }
    }
}
