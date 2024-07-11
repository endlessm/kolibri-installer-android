package org.endlessos.key;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.Toolbar;

import java.io.BufferedInputStream;
import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.zip.ZipEntry;
import java.util.zip.ZipException;
import java.util.zip.ZipInputStream;

public class SettingsActivity extends Activity {
    // TODO: Add a way back to the main activity.
    // TODO: Restart the Kolibri service if it is running.
    // TODO: Show progress while importing.
    // TODO: Disable the import button while importing.
    // TODO: Display helpful information after importing.

    private static final String TAG = Constants.TAG;

    private static final int CHOOSE_FILE_RESULT_CODE = 8778;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_settings);

        getActionBar().setTitle("Endless Key Settings");

        final Button importContentButton = findViewById(R.id.importContentButton);
        importContentButton.setOnClickListener(
                new View.OnClickListener() {

                    @Override
                    public void onClick(View view) {
                        Log.i("importContent", "onClick");
                        startImportContent();
                    }
                }
        );
    }

    private void startImportContent() {
        Intent chooseFile = new Intent(Intent.ACTION_GET_CONTENT);
        chooseFile.addCategory(Intent.CATEGORY_OPENABLE);
        chooseFile.setType("application/zip");
        startActivityForResult(
                Intent.createChooser(chooseFile, "Choose a file"),
                CHOOSE_FILE_RESULT_CODE
        );
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);

        if (requestCode != CHOOSE_FILE_RESULT_CODE) {
            return;
        }

        if (resultCode != Activity.RESULT_OK) {
            return;
        }

        try {
            copyKolibriContent(
                    data.getData(),
                    KolibriUtils.getKolibriHome(getBaseContext())
            );
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    protected void copyKolibriContent(Uri sourceContent, File outputDirectory) throws IOException {
        InputStream fileInput;

        fileInput = getContentResolver().openInputStream(sourceContent);

        ZipInputStream zipInput = new ZipInputStream(new BufferedInputStream(fileInput));
        ZipEntry zipEntry = null;
        byte[] buffer = new byte[1024];

        while (true) {
            String fileName;
            File outputFile;

            zipEntry = zipInput.getNextEntry();

            if (zipEntry == null) {
                break;
            }

            fileName = zipEntry.getName();

            if (!fileName.startsWith("content/")) {
                Log.d(TAG, "Content file has wrong parent directory: " + fileName);
                break;
            }

            if (fileName.equals("content/manifest.json")) {
                Long timeSeconds = System.currentTimeMillis() / 1000;
                fileName = "content/manifest."+timeSeconds+".json";
            }

            outputFile = new File(outputDirectory, fileName);

            if (zipEntry.isDirectory()) {
                try {
                    outputFile.mkdirs();
                } catch (SecurityException error) {
                    error.printStackTrace();
                }
            } else {
                int count;
                FileOutputStream fileOutput;

                fileOutput = new FileOutputStream(outputFile);

                while (true) {
                    count = zipInput.read(buffer);

                    if (count == -1) {
                        break;
                    }

                    fileOutput.write(buffer, 0, count);
                }

                fileOutput.close();
                zipInput.closeEntry();
            }
        }
    }
}