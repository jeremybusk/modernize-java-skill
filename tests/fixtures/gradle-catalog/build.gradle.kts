plugins { application }
repositories {
    System.getenv("JAVA_MODERNIZE_M2_REPO")?.let { maven { url = uri(it) } }
    mavenCentral()
}
java { toolchain { languageVersion.set(JavaLanguageVersion.of(21)) } }
tasks.withType<JavaCompile>().configureEach { options.release.set(17) }
application { mainClass.set("example.Main") }
dependencies {
    testImplementation(platform(libs.junit.bom))
    testImplementation(libs.junit.jupiter)
    testRuntimeOnly(libs.junit.launcher)
}
tasks.test { useJUnitPlatform() }
dependencyLocking { lockAllConfigurations() }
