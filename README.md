# Kolibri Android Installer

An Android application for Kolibri. [Chaquopy][chaquopy] is used to
access Python from the Android runtime.

[chaquopy]: https://chaquo.com/chaquopy/

The application consists of 2 components:

1. An Android [service][android-service] running Kolibri.
2. An Android [webview][android-webview] running as the main
   [activity][android-activity].

[android-service]: https://developer.android.com/guide/components/services
[android-webview]: https://developer.android.com/develop/ui/views/layout/webapps/webview
[android-activity]: https://developer.android.com/guide/components/activities/intro-activities

## Installing from Google Play Store

The Kolibri application is available in [Google Play Store][play-store]
as Endless Key using the app ID `org.endlessos.Key`. Endless users
should disable analytics as explained
[below](#enabling-or-disabling-analytics-and-crashlytics).

[play-store]: https://play.google.com/store/apps

## Building for Development

1. Install Java 17 and python3:
   ```
   apt install openjdk-17-jdk-headless python3 python3-pip
   ```

2. Install the Android SDK:
   ```
   make sdk
   ```
   This will install the SDK in `$ANDROID_HOME` (`~/.android/sdk` by default).

3. Install the Python dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Build the debug and release APKs:
   ```
   ./gradlew build
   ```

5. Run the [instrumented tests][android-instrumented] tests:
   ```
   ./gradlew allDevicesCheck
   ```
   See the [documentation][android-test-cli] for more details on running tests
   from the command line.

[android-instrumented]: https://developer.android.com/training/testing/instrumented-tests
[android-test-cli]: https://developer.android.com/studio/test/command-line

## Build on Toolbox

Toolbox allows a mixture of the above build processes by providing a
development environment inside a container.

1. Install [toolbox](https://containertoolbx.org/)

2. Run `make build_toolbox`.

3. Run `toolbox enter android_kolibri` to enter the container.

4. Continue at step 3 in [Building for development](#building-for-development).

### Custom Explore Plugin version

By default, kolibri-installer-android includes the newest released version of
[kolibri-explore-plugin](https://github.com/endlessm/kolibri-explore-plugin).
To test a different version, set the `exploreUrl` and `appsBundleUrl` in
`~/.gradle/gradle.properties`:

```
exploreUrl=file:///path/to/kolibri_explore_plugin.whl
appsBundleUrl=file:///path/to/apps-bundle.zip
```

## Signing release builds

In order to upload APKs or AABs to Google Play, they need to be signed by a
trusted key. A signing configuration for released builds will be created if the
`upload.properties` file is present. This is a Java properties file with the
following required keys:

* `storeFile` - Path to the Java keystore file.
* `storePassword` - Password for the Java keystore.
* `keyAlias` - Alias of the signing key with the keystore.
* `keyPassword` (optional) - Password for the signing key. If this is not set,
  the keystore password will be used.

## Installing the apk

1. Connect your Android device over USB, with USB Debugging enabled.

2. Ensure that `adb devices` brings up your device.

3. Run `./gradlew installDebug` to install onto the device.


## Running the apk from the terminal

1. Run `adb shell am start -n org.endlessos.Key/org.endlessos.key.KolibriActivity`

## Debugging the app

### Server Side
To get all debug logs from the application, run:

```
adb logcat '*:F' EndlessKey EKWebConsole AndroidRuntime python.stdout python.stderr
```

### Client side
1. Start the Kolibri server via Android app
2. Open a browser and see debug logs
  - If your device doesn't aggressively kill the server, you can open Chrome and use remote debugging tools to see the logs on your desktop.
  - You can also leave the app open and port forward the Android device's Kolibri port using [adb](https://developer.android.com/studio/command-line/adb#forwardports):
  ```
  adb forward tcp:8080 tcp:8081
  ```
  then going into your desktop's browser and accessing `localhost:8081`. Note that you can map to any port on the host machine, the second argument.

Alternatively, you can debug the webview directly. Modern Android versions should let you do so from the developer settings.

You could also do so using [Weinre](https://people.apache.org/~pmuellr/weinre/docs/latest/Home.html). Visit the site to learn how to install and setup. You will have to build a custom Kolibri .whl file that contains the weinre script tag in the [base.html file](https://github.com/learningequality/kolibri/blob/develop/kolibri/core/templates/kolibri/base.html).

## Firebase Analytics and Crashlytics

Metrics and crashes are collected from the application using Firebase
[Analytics][firebase_analytics] and [Crashlytics][firebase_crashlytics].
In order to see details of the information being collected, increase the
log levels for the relevant tags:

```
adb shell setprop log.tag.FA VERBOSE
adb shell setprop log.tag.FA-SVC VERBOSE
adb shell setprop log.tag.FirebaseCrashlytics DEBUG
```

Normally the analytics events are cached locally on disk and sent to the
Firebase server periodically. In order to send the events immediately,
enable Analytics debug mode for this application:

```
adb shell setprop debug.firebase.analytics.app org.endlessos.Key
```

Finally, events can be seen in the Firebase console
[DebugView][firebase_debugview] in realtime by setting the application
as the Android [debug app][android_debugapp]. This requires enabling
`Developer options` on the device, choosing `Select debug app`, and
setting it to `org.endlessos.Key`.

[firebase_analytics]: https://firebase.google.com/docs/analytics
[firebase_crashlytics]: https://firebase.google.com/docs/crashlytics
[firebase_debugview]: https://firebase.google.com/docs/analytics/debugview
[android_debugapp]: https://developer.android.com/studio/debug/dev-options#debugging

### Enabling or disabling Analytics and Crashlytics

By default, Analytics and Crashlytics are enabled on release builds and
disabled on debug builds. This prevents development work from polluting
our production metrics. Event collection can be explicitly enabled or
disabled at runtime using the `debug.org.endlessos.key.analytics` system
property. For example:

```
adb shell setprop debug.org.endlessos.key.analytics true
```

The primary use case is for testing analytics development on debug
builds. However, it can also be used to opt out of analytics by setting
the property value to `false`. Endless testing users should explicitly
disable analytics on release builds so that production metrics are not
affected by test usage.

## Helpful commands
- [adb](https://developer.android.com/studio/command-line/adb) is pretty helpful. Here are some useful uses:
  - `adb logcat -b all -c` will clear out the device's log. ([Docs](https://developer.android.com/studio/command-line/logcat))
    - Logcat also has a large variety of filtering options. Check out
      the docs for those. Particularly, the filter `*:S` silences all
      tags without a filterspec. Combined with a desired tag, this will
      show only logs from that tag. The `adb` CLI option `-s` is a
      shorthand for `*:S`, so `adb logcat -s SomeTag` will only show
      logs from `SomeTag`. Alternatively, `*:F` will show only fatal
      logs from other tags.
  - Uninstall from terminal using `adb shell pm uninstall org.endlessos.Key`. ([Docs](https://developer.android.com/studio/command-line/adb#pm))
- Docker shouldn't be rebuilding very often, so it shouldn't be using that much storage. But if it does, you can run `docker system prune` to clear out all "dangling" images, containers, and layers. If you've been constantly rebuilding, it will likely get you several gigabytes of storage.

## Using the Android Emulator

Installing the APK to a real device during development is slow. Instead, the
[Android Emulator](https://developer.android.com/studio/run/emulator) can be
used for faster installs in a clean environment. The recommended way to use
the emulator is through Android Studio, but it can also be invoked directly.

First, ensure the emulator is installed in the Android SDK. The `make setup`
target will install the necessary pieces. Assuming the SDK is installed in
`/opt/android/sdk`:

```
/opt/android/sdk/cmdline-tools/latest/bin/sdkmanager emulator
```

Next, install a platform and system image:

```
/opt/android/sdk/cmdline-tools/latest/bin/sdkmanager "platforms;android-34"
/opt/android/sdk/cmdline-tools/latest/bin/sdkmanager "system-images;android-34;google_apis_playstore;x86_64"
```

Now an [Android Virtual Device
(AVD)](https://developer.android.com/studio/run/managing-avds) needs to be
created. This can be done from the command line with
[avdmanager](https://developer.android.com/studio/command-line/avdmanager).

There are many device definitions available. To see the list, run:

```
/opt/android/sdk/cmdline-tools/latest/bin/avdmanager list device
```

To create an AVD, a name, system image and device must be provided. Assuming
the system image provided above and a Pixel 5 device:

```
/opt/android/sdk/cmdline-tools/latest/bin/avdmanager create avd --name test \
  --package "system-images;android-34;google_apis_playstore;x86_64" --device pixel_5
```

The AVD should be ready now and `avdmanager list avd` will show the details.
Start it [from the
emulator](https://developer.android.com/studio/run/emulator-commandline):

```
/opt/android/sdk/emulator/emulator -avd test
```

A window should show up showing Android booting. Once it's running, it can be
connected to with `adb` in all the ways shown above. When you're done with the
emulator, you can stop it with `Ctrl-C` from the terminal where you started
it. By default, the emulator stores snapshots and the next time you start that
AVD it will be in the same state.

### Emulator SD Card

The Android Emulator does not support removable storage such as USB drives.
However, you can approximate that experience using an SD card. By default,
`avdmanager` will not create an SD card connected to the device. To use one,
add `--sdcard 1G` to the `avdmanager create avd` command above. That will
create a 1 GB card image, but other sizes can be used with typical suffixes
like `M` for MB.

The SD card can be populated within Android from the file manager, but this
can be cumbersome. Instead, you can work with the SD card image from the host.
Run `avdmanager list avd` to get the path to the AVD that was created. The SD
card disk image will be in that directory named `sdcard.img`. This is a raw
disk image with no partitions containing a FAT filesystem. Once the emulator
is started, a second file named `sdcard.img.qcow2` will be created. This is a
[QEMU disk
image](https://www.qemu.org/docs/master/system/qemu-block-drivers.html#cmdoption-image-formats-arg-qcow2)
that's setup to use the original `sdcard.img` file as a read only base image.
Once the qcow2 image has been created, any changes to the `sdcard.img` file
will not be reflected in the SD card seen in the emulator.

If the emulator hasn't been run yet, the raw disk image can be updated to
include any desired files by mounting the FAT filesystem locally. First,
create a loop block device pointing to the raw disk image:

```
sudo losetup --show -f ~/.android/avd/test.avd/sdcard.img
```

This will show the connected loop device. Assuming the first device,
`/dev/loop0`, it can now be mounted:

```
sudo mount /dev/loop0 /mnt
```

Now the filesystem will be mounted at `/mnt` and files can be added or
removed. When done, unmount the filesystem and disconnect the loop device:

```
sudo umount /mnt
sudo losetup -d /dev/loop0
```

If the qcow2 image has already been created, it can be accessed with some help
from QEMU's network block device (NBD) server,
[qemu-nbd](https://www.qemu.org/docs/master/tools/qemu-nbd.html). This tool is
included in the `qemu-utils` package on Debian systems.

First, ensure that the kernel's `nbd` module is loaded:

```
sudo modprobe nbd
```

Now a network block device can be connected and mounted similar to the above
raw image usage:

```
sudo qemu-nbd -c /dev/nbd0 ~/.android/avd/test.avd/sdcard.img.qcow2
sudo mount /dev/nbd0 /mnt
```

When done, unmount the filesystem and disconnect the block device:

```
sudo umount /mnt
sudo qemu-nbd -d /dev/nbd0
```

In order to share an SD card among multiple AVDs, one can be created ahead of
time using the emulator's `mksdcard` tool:

```
/opt/android/sdk/emulator/mksdcard 512M ~/.android/avd/test-sdcard.img
```

This would create a 512 MB SD card image at `~/.android/avd/test-sdcard.img`.
When creating an AVD, provide this path to the `--sdcard` option instead of
providing a size. Once this image is used is an emulator, a qcow2 image will
be created wrapping it at `~/.android/avd/test-sdcard.img.qcow2`. In this way,
it can be accessed from the host in the same ways as an SD card image created
by `avdmanager`.
