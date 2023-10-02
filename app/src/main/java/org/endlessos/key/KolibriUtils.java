package org.endlessos.key;

import android.annotation.SuppressLint;
import android.content.Context;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.content.pm.PackageManager.ApplicationInfoFlags;
import android.os.Build;
import android.os.Bundle;

import androidx.annotation.Nullable;

import java.lang.reflect.Method;

/** Kolibri utility functions. */
public class KolibriUtils {
    /**
     * Returns the application's metadata.
     *
     * <p>The metadata corresponds to the application <code>&lt;meta-data&gt;</code> entries in the
     * Android manifest. If the application information cannot be retrieved, <code>null</code> is
     * returned.
     *
     * @param context the application context
     * @return the application's metadata
     */
    @Nullable
    @SuppressWarnings("deprecation")
    public static Bundle getAppMetaData(Context context) {
        final PackageManager manager = context.getPackageManager();
        final String pkgName = context.getPackageName();
        final ApplicationInfo appInfo;

        try {
            // getApplicationInfo(String, int) is deprecated in API 33.
            if (Build.VERSION.SDK_INT < 33) {
                appInfo = manager.getApplicationInfo(pkgName, PackageManager.GET_META_DATA);
            } else {
                appInfo =
                        manager.getApplicationInfo(
                                pkgName, ApplicationInfoFlags.of(PackageManager.GET_META_DATA));
            }
        } catch (PackageManager.NameNotFoundException e) {
            Logger.e("Could not get application metadata", e);
            return null;
        }

        return appInfo.metaData;
    }

    @SuppressLint("PrivateApi")
    public static boolean getSysPropBoolean(String key, boolean defaultValue) {
        // The SystemProperties class is not exported in the SDK, so we need to resolve the class at
        // runtime.
        final Class<?> SystemProperties;
        try {
            SystemProperties = Class.forName("android.os.SystemProperties");
        } catch (ClassNotFoundException e) {
            Logger.e("Could not load android.os.SystemProperties class", e);
            return defaultValue;
        }

        final Method getBoolean;
        try {
            getBoolean = SystemProperties.getMethod("getBoolean", String.class, boolean.class);
        } catch (Exception e) {
            Logger.e("Failed to find getBoolean method from android.os.SystemProperties class", e);
            return defaultValue;
        }

        try {
            return (Boolean) getBoolean.invoke(null, key, defaultValue);
        } catch (Exception e) {
            Logger.e("Failed to invoke getBoolean from android.os.SystemProperties class", e);
            return defaultValue;
        }
    }
}
