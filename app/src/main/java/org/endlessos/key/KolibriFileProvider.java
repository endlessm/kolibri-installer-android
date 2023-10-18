package org.endlessos.key;

import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;

import androidx.annotation.Nullable;
import androidx.core.content.FileProvider;

import java.io.File;
import java.io.IOException;
import java.net.URLConnection;
import java.nio.file.Files;

/** Kolibri file provider. */
public class KolibriFileProvider extends FileProvider {
    public static final String AUTHORITY = "org.endlessos.kolibrifileprovider";

    public KolibriFileProvider() {
        super(R.xml.fileprovider_paths);
    }

    /**
     * Share a file using a provided Context.
     *
     * <p>This is a convenience method for constructing a file sharing intent and starting an
     * activity to use it.
     *
     * @param context A Context for the current component.
     * @param path The file path to share.
     * @param message The activity chooser title when not sending to a specific package.
     * @param mimeType The file's MIME type. If <code>null</code>, the MIME type will be guessed.
     * @param packageName A specific application package to share the file with. If <code>null
     *     </code>, an activity chooser will be used.
     */
    public static void shareFile(
            Context context,
            String path,
            String message,
            @Nullable String mimeType,
            @Nullable String packageName) {
        final File file = new File(path);

        final Uri uri;
        try {
            uri = getUriForFile(context, AUTHORITY, file);
        } catch (IllegalArgumentException e) {
            Logger.e("File " + path + " cannot be shared", e);
            return;
        }

        if (mimeType == null) {
            mimeType = getFileMimeType(file);
            if (mimeType == null) {
                // Fallback to wild card type as suggested by ACTION_SEND.
                Logger.w("Using */* for MIME type of " + path);
                mimeType = "*/*";
            }
        }

        Intent intent = new Intent(Intent.ACTION_SEND);
        intent.putExtra(Intent.EXTRA_STREAM, uri);
        intent.setType(mimeType);
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);

        // If a specific package isn't specified, wrap the intent in an activity chooser.
        if (packageName != null) {
            intent.setPackage(packageName);
        } else {
            intent = Intent.createChooser(intent, message);
        }

        // If this isn't a UI context (an Activity), start a new task.
        if (!isUiContext(context)) {
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        }

        context.startActivity(intent);
    }

    private static boolean isUiContext(Context context) {
        if (Build.VERSION.SDK_INT >= 31) {
            return context.isUiContext();
        } else {
            return context.getSystemService(Context.WINDOW_SERVICE) != null;
        }
    }

    @Nullable
    private static String getFileMimeType(File file) {
        String mimeType = null;

        // On API 26 the MIME type can be probed.
        if (Build.VERSION.SDK_INT >= 26) {
            try {
                mimeType = Files.probeContentType(file.toPath());
            } catch (IOException e) {
                Logger.w("Could not probe MIME type of " + file, e);
            }
        }

        // Fallback to guessing from the file name on older versions or if probing failed.
        if (mimeType == null) {
            mimeType = URLConnection.guessContentTypeFromName(file.getName());
        }

        return mimeType;
    }
}
