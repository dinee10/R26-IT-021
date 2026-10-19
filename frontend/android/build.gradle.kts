import com.android.build.api.variant.LibraryAndroidComponentsExtension

allprojects {
    repositories {
        google()
        mavenCentral()
    }
}

val newBuildDir: Directory =
    rootProject.layout.buildDirectory
        .dir("../../build")
        .get()
rootProject.layout.buildDirectory.value(newBuildDir)

subprojects {
    val newSubprojectBuildDir: Directory = newBuildDir.dir(project.name)
    project.layout.buildDirectory.value(newSubprojectBuildDir)
}

subprojects {
    project.evaluationDependsOn(":app")
    pluginManager.withPlugin("com.android.library") {
        extensions.configure<LibraryAndroidComponentsExtension> {
            finalizeDsl { libraryDsl ->
                libraryDsl.compileSdk = 36
                libraryDsl.buildToolsVersion = "35.0.0"
            }
        }
    }
    buildscript {
        configurations.configureEach {
            resolutionStrategy.force("com.android.tools.build:gradle:8.13.1")
            resolutionStrategy.force("org.jetbrains.kotlin:kotlin-gradle-plugin:2.2.20")
        }
    }
}

tasks.register<Delete>("clean") {
    delete(rootProject.layout.buildDirectory)
}
