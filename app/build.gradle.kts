// Gradle build script
// https://docs.gradle.org/
// https://docs.gradle.org/current/kotlin-dsl/index.html

import com.android.build.api.dsl.ManagedVirtualDevice

// Gradle plugins
plugins {
    id("com.android.application")
}

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
