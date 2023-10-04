package org.endlessos.key;

import android.annotation.SuppressLint;
import android.content.Context;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.PackageManager.ApplicationInfoFlags;
import android.content.pm.PackageManager.PackageInfoFlags;
import android.content.pm.Signature;
import android.os.Build;
import android.os.Bundle;

import androidx.annotation.Nullable;

import java.io.ByteArrayInputStream;
import java.lang.reflect.Method;
import java.security.cert.CertificateException;
import java.security.cert.CertificateFactory;
import java.security.cert.X509Certificate;
import java.util.Arrays;

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

    /**
     * Returns the package's current signature.
     *
     * <p>If the package information cannot be retrieved, <code>null</code> is returned.
     *
     * @param context the package context
     * @return the signature
     */
    @Nullable
    @SuppressWarnings("deprecation")
    public static Signature getPackageSignature(Context context) {
        final PackageManager manager = context.getPackageManager();
        final String pkgName = context.getPackageName();
        final PackageInfo info;

        // GET_SIGNATURES is deprecated in API 28.
        final int flags =
                (Build.VERSION.SDK_INT < 28)
                        ? PackageManager.GET_SIGNATURES
                        : PackageManager.GET_SIGNING_CERTIFICATES;
        try {
            // getPackageInfo(String, int) is deprecated in API 33.
            if (Build.VERSION.SDK_INT < 33) {
                info = manager.getPackageInfo(pkgName, flags);
            } else {
                info = manager.getPackageInfo(pkgName, PackageInfoFlags.of(flags));
            }
        } catch (PackageManager.NameNotFoundException e) {
            Logger.e("Could not get package info", e);
            return null;
        }

        // PackageInfo.signatures is deprecated in API 28.
        final Signature signature;
        if (Build.VERSION.SDK_INT < 28) {
            signature = (info.signatures.length > 0) ? info.signatures[0] : null;
        } else {
            if (info.signingInfo.hasMultipleSigners()) {
                // If there are multiple signers, the current one is last.
                final Signature[] signatures = info.signingInfo.getSigningCertificateHistory();
                signature = (signatures.length > 0) ? signatures[signatures.length - 1] : null;
            } else {
                final Signature[] signatures = info.signingInfo.getApkContentsSigners();
                signature = (signatures.length > 0) ? signatures[0] : null;
            }
        }

        if (signature == null) {
            Logger.w("Package does not contain any signatures");
        }
        return signature;
    }

    /**
     * Returns the package signature's issuing organization.
     *
     * <p>The organization (O) OID is retrieved from the issuer distinguished name in the package
     * signature's X.509 certificate. If the signature can't be found or parsed, or it does not
     * contain an organization, an empty string is returned.
     *
     * @param context the package context
     * @return the issuer organization
     */
    public static String getPackageSignatureIssuerOrg(Context context) {
        final Signature signature = getPackageSignature(context);
        if (signature == null) {
            return "";
        }

        final ByteArrayInputStream sigStream = new ByteArrayInputStream(signature.toByteArray());
        final X509Certificate cert;
        try {
            final CertificateFactory factory = CertificateFactory.getInstance("X509");
            cert = (X509Certificate) factory.generateCertificate(sigStream);
        } catch (CertificateException e) {
            Logger.e("Could not parse package signature", e);
            return "";
        }

        final String issuer = cert.getIssuerX500Principal().getName();
        return Arrays.stream(issuer.split(","))
                .filter(attr -> attr.startsWith("O="))
                .map(org -> org.replaceFirst("^O=", ""))
                .findFirst()
                .orElse("");
    }

    /**
     * Returns the string to use for the KOLIBRI_RUN_MODE environment variable.
     *
     * @param context the package context
     * @return the KOLIBRI_RUN_MODE string
     */
    public static String getKolibriRunMode(Context context) {
        final String org = getPackageSignatureIssuerOrg(context);
        if (org.equals("Learning Equality") || org.equals("Endless OS Foundation LLC")) {
            return "android-testing";
        } else if (org.equals("Android")) {
            // Generated debug certificate.
            return "android-debug";
        } else if (org.equals("Google Inc.")) {
            // Google Play Store.
            return "";
        } else {
            return "android-" + org.toLowerCase().replaceAll("\\s", "-").replaceAll("\\W", "");
        }
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
