// Gradle build script
// https://docs.gradle.org/
// https://docs.gradle.org/current/kotlin-dsl/index.html

import com.android.build.api.dsl.ManagedVirtualDevice
import com.android.build.api.variant.Variant
import com.android.build.api.variant.VariantOutputConfiguration.OutputType
import groovy.json.JsonSlurper
import java.time.Instant

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

// Configure the app's versionCode. We do this once here so that all
// variants use the same version.
val versionCode: String by project
var versionCodeValue: Int
if (!versionCode.isBlank()) {
    logger.info("Using versionCode property")
    versionCodeValue = versionCode.toInt()
} else {
    // Use the current time in seconds.
    logger.info("Using current time for versionCode")
    versionCodeValue = Instant.now().getEpochSecond().toInt()
}
logger.quiet("Using versionCode {}", versionCodeValue)

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

// Tasks
// https://docs.gradle.org/current/userguide/more_about_tasks.html

// Create a task per variant that generates a JSON file with version
// names that will be used to set versionName below. The JSON file is
// also used by the upload job to read the various versions, so the
// versionCode is included in it.
fun createVersionTask(variant: Variant): TaskProvider<Exec> {
    val taskVariant = variant.name.replaceFirstChar { it.uppercase() }
    return tasks.register<Exec>("output${taskVariant}Version") {
        val pkgdir = layout.buildDirectory.dir("python/pip/${variant.name}/common")
        val output = layout.buildDirectory.file("outputs/version-${variant.name}.json")
        commandLine(
            "./scripts/versions.py",
            "--version-code",
            versionCodeValue.toString(),
            "--pkgdir",
            pkgdir.get().asFile.path,
            "--output",
            output.get().asFile.path,
        )
        inputs.dir(pkgdir)
        outputs.file(output)
    }
}

// Connect our tasks to external tasks.
val variants = ArrayList<Variant>()

// AGP extension API
// https://developer.android.com/build/extend-agp
// AGP extension API
// https://developer.android.com/build/extend-agp
androidComponents {
    onVariants { variant ->
        // Keep track of the variant for use in afterEvalute.
        variants.add(variant)

        // Set versionCode and versionName.
        val versionTask = createVersionTask(variant)
        val versionName = versionTask.map { task ->
            val versionFile = task.outputs.files.singleFile

            // It would be better to use the type safe kotlin JSON serialization library to parse,
            // but gradle doesn't know to include the library at build time unless you use a
            // separate buildSrc project. Just use the groovy JSON library with unsafe casts for
            // now.
            val slurper = JsonSlurper()

            @Suppress("UNCHECKED_CAST")
            val versionData = slurper.parse(versionFile) as Map<String, String>
            versionData.getValue("versionName")
        }
        variant.outputs
            .filter { it.outputType == OutputType.SINGLE }
            .forEach {
                it.versionCode.set(versionCodeValue)
                it.versionName.set(versionName)
            }
    }
}

// In order to support older AGP versions, chaquopy creates its tasks from afterEvaluate. In order
// to hook into those, we need to use an action from an inner afterEvaluate so that it runs after
// all previously added afterEvaluate actions complete.
//
// https://docs.gradle.org/current/kotlin-dsl/gradle/org.gradle.api/-project/after-evaluate.html
project.afterEvaluate {
    project.afterEvaluate {

        // Python package assets are created per build variant, so any tasks that depend on those
        // also have to be created for each variant.
        variants.forEach { variant ->
            val taskVariant = variant.name.replaceFirstChar { it.uppercase() }
            val requirementsTask = tasks.named("generate${taskVariant}PythonRequirements")

            // Make the version task depend on the extracted package files.
            val versionTask = tasks.named("output${taskVariant}Version")
            versionTask.configure {
                inputs.files(requirementsTask)
            }
        }
    }
}
