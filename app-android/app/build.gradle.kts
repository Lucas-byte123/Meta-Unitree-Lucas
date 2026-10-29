import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
  alias(libs.plugins.android.application)
  alias(libs.plugins.jetbrains.kotlin.android)
  alias(libs.plugins.compose.compiler)
}

android {
  namespace = "com.metaunitree.gestos"
  compileSdk = 36

  defaultConfig {
    applicationId = "com.metaunitree.gestos"
    minSdk = 31
    targetSdk = 36
    versionCode = 1
    versionName = "0.1"

    // SDK dos óculos: com o Developer Mode ligado no app Meta AI, os dois valem "0".
    // Sem Developer Mode, vêm do projeto no Wearables Developer Center.
    manifestPlaceholders["mwdat_application_id"] = "0"
    manifestPlaceholders["mwdat_client_token"] = "0"
  }

  buildFeatures { compose = true }

  // o MediaPipe lê o modelo direto do APK
  androidResources { noCompress += "task" }

  compileOptions {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
  }
}

kotlin { compilerOptions { jvmTarget = JvmTarget.JVM_17 } }

dependencies {
  implementation(libs.androidx.activity.compose)
  implementation(platform(libs.androidx.compose.bom))
  implementation(libs.androidx.material3)
  implementation(libs.androidx.lifecycle.runtime.compose)
  implementation(libs.androidx.camera.camera2)
  implementation(libs.androidx.camera.lifecycle)
  implementation(libs.androidx.camera.view)
  implementation(libs.mediapipe.tasks.vision)
  implementation(libs.okhttp)
  implementation(libs.mwdat.core)
  implementation(libs.mwdat.camera)
  implementation(libs.mwdat.mockdevice)

  testImplementation(libs.junit)
}

// Mesmo modelo do mvp-gesto. Fica fora do git (*.task); baixado no primeiro build.
val baixarModelo by tasks.registering {
  val destino = layout.projectDirectory.file("src/main/assets/gesture_recognizer.task").asFile
  outputs.file(destino)
  onlyIf { !destino.exists() }
  doLast {
    val url = "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/" +
      "gesture_recognizer/float16/1/gesture_recognizer.task"
    destino.parentFile.mkdirs()
    uri(url).toURL().openStream().use { entrada -> destino.outputStream().use { entrada.copyTo(it) } }
  }
}
tasks.named("preBuild") { dependsOn(baixarModelo) }
