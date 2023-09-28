pluginManagement {
    repositories {
        // Forked repo with unreleased chaquopy
        // FIXME: Remove this when 15.0.1 is released and published
        maven {
            url = uri("https://dbnicholson.github.io/chaquopy/")
        }
        gradlePluginPortal()
        google()
        mavenCentral()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}
rootProject.name = "Endless Key Android"
include(":app")
