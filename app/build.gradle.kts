// Gradle build script
// https://docs.gradle.org/
// https://docs.gradle.org/current/kotlin-dsl/index.html

import com.android.build.api.dsl.ManagedVirtualDevice
import com.android.build.api.variant.Variant
import com.android.build.api.variant.VariantOutputConfiguration.OutputType
import de.undercouch.gradle.tasks.download.Download
import groovy.json.JsonSlurper
import java.time.Instant

// Gradle plugins
plugins {
    id("com.android.application")
    id("com.chaquo.python")
    id("com.google.gms.google-services")
    id("de.undercouch.download")
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

// Bundle URLs
val appsBundleUrl: String by project
val appsBundleDownloadUrl = if (!appsBundleUrl.isBlank()) {
    appsBundleUrl
} else {
    "https://github.com/endlessm/kolibri-explore-plugin/releases/download/" +
        "v$exploreVersion/apps-bundle.zip"
}
val loadingScreenUrl: String by project
val loadingScreenDownloadUrl = if (!loadingScreenUrl.isBlank()) {
    loadingScreenUrl
} else {
    "https://github.com/endlessm/kolibri-explore-plugin/releases/download/" +
        "v$exploreVersion/loading-screen.zip"
}
val collectionsVersion: String by project
val collectionsUrl: String by project
val collectionsDownloadUrl = if (!collectionsUrl.isBlank()) {
    collectionsUrl
} else {
    "https://github.com/endlessm/endless-key-collections/releases/download/" +
        "v$collectionsVersion/collections.zip"
}

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

            // Enable analytics by default for release builds.
            manifestPlaceholders["analytics_enabled"] = "true"
        }

        getByName("debug") {
            // Disable analytics by default for debug builds.
            manifestPlaceholders["analytics_enabled"] = "false"
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
        extractPackages("kolibri_android.plugin.migrations")
    }
}

// App dependencies
dependencies {
    implementation("androidx.annotation:annotation:1.7.0")

    // Firebase Analytics
    implementation(platform("com.google.firebase:firebase-bom:32.3.1"))
    implementation("com.google.firebase:firebase-analytics")

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

// Create a task per variant that prunes unwanted files from the extracted
// python packages.
fun createPruneTask(variant: Variant): TaskProvider<Exec> {
    val taskVariant = variant.name.replaceFirstChar { it.uppercase() }
    return tasks.register<Exec>("prune${taskVariant}PythonPackages") {
        val pkgroot = layout.buildDirectory.dir("python/pip/${variant.name}")
        val report = layout.buildDirectory.file("outputs/logs/prune-${variant.name}-report.txt")
        commandLine(
            "./scripts/prunepackages.py",
            "--pkgroot",
            pkgroot.get().asFile.path,
            "--report",
            report.get().asFile.path,
        )
    }
}

// Download and extract apps-bundle.zip into the python source directory. Chaquopy will
// automatically extract its data files to the filesystem at runtime.
val appsBundleDirectory: Directory = layout.projectDirectory.dir(
    "src/main/python/kolibri_android/apps",
)

val downloadAppsBundleTask = tasks.register<Download>("downloadAppsBundle") {
    src(appsBundleDownloadUrl)
    dest(layout.buildDirectory.file("download/apps-bundle-$exploreVersion.zip"))
    onlyIfModified(true)
    useETag(true)
}

val extractAppsBundleTask = tasks.register<Copy>("extractAppsBundle") {
    from(zipTree(downloadAppsBundleTask.map { it.dest })) {
        // Strip the embedded subdirectory so we can extract to an explicit subdirectory.
        eachFile {
            relativePath = RelativePath(true, *relativePath.segments.drop(1).toTypedArray())
        }
        includeEmptyDirs = false
    }
    into(appsBundleDirectory)
}

val cleanAppsBundleTask = tasks.register<Delete>("cleanAppsBundle") {
    delete(appsBundleDirectory)
}

// Download loading-screen.zip
val downloadLoadingScreenTask = tasks.register<Download>("downloadLoadingScreen") {
    src(loadingScreenDownloadUrl)
    dest(layout.buildDirectory.file("download/loading-screen-$exploreVersion.zip"))
    onlyIfModified(true)
    useETag(true)
}

// Download and extract collections.zip into the python source directory. Chaquopy will
// automatically extract its data files to the filesystem at runtime.
val collectionsDirectory: Directory = layout.projectDirectory.dir(
    "src/main/python/kolibri_android/collections",
)

val downloadCollectionsTask = tasks.register<Download>("downloadCollections") {
    src(collectionsDownloadUrl)
    dest(layout.buildDirectory.file("download/collections-$collectionsVersion.zip"))
    onlyIfModified(true)
    useETag(true)
}

val extractCollectionsTask = tasks.register<Copy>("extractCollections") {
    from(zipTree(downloadCollectionsTask.map { it.dest }))
    into(collectionsDirectory)
}

val cleanCollectionsTask = tasks.register<Delete>("cleanCollections") {
    delete(collectionsDirectory)
}

// Task class for collecting build assets. This needs to be a class that accepts a DirectoryProperty
// that can be set by AGP's addGeneratedSourceDirectory. It would be nice to use Copy directly, but
// that doesn't have a DirectoryProperty.
abstract class CollectBuildAssetsTask : DefaultTask() {
    // Path to the downloaded loading-screen.zip.
    @get:InputFile
    abstract val loadingScreenZip: RegularFileProperty

    // The output directory to be set by AGP.
    @get:OutputDirectory
    abstract val outputDir: DirectoryProperty

    @TaskAction
    fun run() {
        val proj = getProject()
        val dest = outputDir.get()
        proj.delete(dest)
        proj.mkdir(dest)
        proj.copy {
            from(proj.zipTree(loadingScreenZip.get())) {
                // loading-screen.zip is flat, so prepend a subdirectory.
                eachFile {
                    relativePath = relativePath.prepend("loadingScreen")
                }
                includeEmptyDirs = false
            }
            into(dest)
        }
    }
}

// The actual build assets task.
val collectBuildAssetsTask = tasks.register<CollectBuildAssetsTask>("collectBuildAssets") {
    inputs.files(downloadLoadingScreenTask)
    loadingScreenZip.set(
        // Coerce the File into a RegularFileProperty.
        downloadLoadingScreenTask.flatMap {
            getObjects().fileProperty().fileValue(it.dest)
        },
    )
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

        // Add the build assets.
        variant.sources.assets?.addGeneratedSourceDirectory(
            collectBuildAssetsTask,
            CollectBuildAssetsTask::outputDir,
        )
    }
}

// In order to support older AGP versions, chaquopy creates its tasks from afterEvaluate. In order
// to hook into those, we need to use an action from an inner afterEvaluate so that it runs after
// all previously added afterEvaluate actions complete.
//
// https://docs.gradle.org/current/kotlin-dsl/gradle/org.gradle.api/-project/after-evaluate.html
project.afterEvaluate {
    project.afterEvaluate {
        // Add extracted apps-bundle and collections files as inputs to extracting the local python
        // files.
        tasks.named("extractPythonBuildPackages").configure {
            inputs.files(extractAppsBundleTask)
            inputs.files(extractCollectionsTask)
        }

        // Python package assets are created per build variant, so any tasks that depend on those
        // also have to be created for each variant.
        variants.forEach { variant ->
            val taskVariant = variant.name.replaceFirstChar { it.uppercase() }
            val requirementsTask = tasks.named("generate${taskVariant}PythonRequirements")
            val requirementsAssetsTask = tasks.named(
                "generate${taskVariant}PythonRequirementsAssets",
            )

            // Make the version task depend on the extracted package files.
            val versionTask = tasks.named("output${taskVariant}Version")
            versionTask.configure {
                inputs.files(requirementsTask)
            }

            // Order the pruning task after the packages have been extracted
            // but before they've been zipped into assets.
            val pruneTask = createPruneTask(variant)
            pruneTask.configure {
                inputs.files(requirementsTask)
            }
            requirementsAssetsTask.configure {
                // dependsOn is used here instead of wiring the prune task
                // outputs since there aren't any outputs.
                dependsOn(pruneTask)
            }
        }
    }
}

// Make the generic clean task depend on our custom clean tasks.
tasks.named("clean").configure {
    dependsOn(cleanAppsBundleTask)
    dependsOn(cleanCollectionsTask)
}
