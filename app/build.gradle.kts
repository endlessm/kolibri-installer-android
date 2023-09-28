// Gradle build script
// https://docs.gradle.org/
// https://docs.gradle.org/current/kotlin-dsl/index.html

import com.android.build.api.dsl.ManagedVirtualDevice

// Gradle plugins
plugins {
    id("com.android.application")
    id("com.chaquo.python")
}

// Configure package versions and/or URLs from properties so they're easier to update or override.
val kolibriVersion: String by project
val kolibriUrl: String by project
val kolibriSpec = if (!kolibriUrl.isBlank()) kolibriUrl else "kolibri==$kolibriVersion"
val exploreVersion: String by project
val exploreUrl: String by project
val exploreSpec = if (!exploreUrl.isBlank()) {
    exploreUrl
} else {
    "kolibri-explore-plugin==$exploreVersion"
}
val zimVersion: String by project
val zimUrl: String by project
val zimSpec = if (!zimUrl.isBlank()) zimUrl else "kolibri-zim-plugin==$zimVersion"

// Android (AGP) configuration
// https://developer.android.com/build/
// https://developer.android.com/reference/tools/gradle-api
android {
    // Main Java namespace
    namespace = "org.endlessos.key"

    compileSdk = 33

    defaultConfig {
        // App ID. Customarily this is lowercase and matches the Java
        // namespace, but we've already published with Key uppercased.
        applicationId = "org.endlessos.Key"

        targetSdk = 33
        minSdk = 24
        versionCode = 1
        versionName = "1.0"

        ndk {
            abiFilters += listOf("armeabi-v7a", "arm64-v8a", "x86", "x86_64")
        }

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        getByName("release") {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android.txt"), "proguard-rules.pro")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_1_8
        targetCompatibility = JavaVersion.VERSION_1_8
    }

    testOptions {
        // https://developer.android.com/studio/test/gradle-managed-devices
        // https://developer.android.com/reference/tools/gradle-api/8.1/com/android/build/api/dsl/ManagedVirtualDevice
        managedDevices {
            devices {
                maybeCreate<ManagedVirtualDevice>("desktop33").apply {
                    // Use device profiles you typically see in Android Studio. See avdmanager list
                    // device.
                    device = "Medium Desktop"
                    // Google automated test device. Use aosp-atd to test without Google APIs.
                    systemImageSource = "google-atd"
                    apiLevel = 33
                }
            }
        }
    }
}

// Chaquopy configuration
// https://chaquo.com/chaquopy/doc/15.0/android.html
chaquopy {
    defaultConfig {
        // Python version
        version = "3.9"

        // Packages to install with pip.
        pip {
            install(kolibriSpec)
            install(exploreSpec)
            install(zimSpec)
        }

        // Django migrations in 1.11 work by looking for modules in the filesystem, so any packages
        // containing them need to be extracted rather than loaded directly from the asset zip file.
        // Unfortunately, chaquopy will include both the compiled and non-compiled modules in this
        // case. For the giant kolibri wheel that's quite a bit of bloat, so only choose migrations
        // packages. When upgrading kolibri, check this is still correct.
        //
        // https://github.com/chaquo/chaquopy/issues/978
        extractPackages("kolibri.core.analytics.migrations")
        extractPackages("kolibri.core.auth.migrations")
        extractPackages("kolibri.core.bookmarks.migrations")
        extractPackages("kolibri.core.content.migrations")
        extractPackages("kolibri.core.device.migrations")
        extractPackages("kolibri.core.discovery.migrations")
        extractPackages("kolibri.core.exams.migrations")
        extractPackages("kolibri.core.lessons.migrations")
        extractPackages("kolibri.core.logger.migrations")
        extractPackages("kolibri.core.notifications.migrations")
        extractPackages("kolibri.dist.django.contrib.admin.migrations")
        extractPackages("kolibri.dist.django.contrib.auth.migrations")
        extractPackages("kolibri.dist.django.contrib.contenttypes.migrations")
        extractPackages("kolibri.dist.django.contrib.flatpages.migrations")
        extractPackages("kolibri.dist.django.contrib.redirects.migrations")
        extractPackages("kolibri.dist.django.contrib.sessions.migrations")
        extractPackages("kolibri.dist.django.contrib.sites.migrations")
        extractPackages("kolibri.dist.morango.migrations")
        extractPackages("kolibri.dist.rest_framework.authtoken.migrations")
        extractPackages("kolibri_explore_plugin.migrations")
    }
}

// App dependencies
dependencies {
    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test:core:1.5.0")
    androidTestImplementation("androidx.test:runner:1.5.2")
    androidTestImplementation("androidx.test:rules:1.5.0")
    // Required by the androidx.test artifacts.
    androidTestImplementation("androidx.core:core-ktx:1.10.1")
}

// Enable Java deprecation warnings and unchecked linting.
tasks.withType<JavaCompile>().configureEach {
    options.setDeprecation(true)
    options.compilerArgs.add("-Xlint:unchecked")
}
