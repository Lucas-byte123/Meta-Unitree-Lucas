package com.metaunitree.gestos

import android.content.Context
import android.graphics.Bitmap
import android.util.Log
import com.google.mediapipe.framework.image.BitmapImageBuilder
import com.google.mediapipe.tasks.core.BaseOptions
import com.google.mediapipe.tasks.vision.core.RunningMode
import com.google.mediapipe.tasks.vision.gesturerecognizer.GestureRecognizer

/** Um dos 21 pontos da mão, em fração da imagem (0 a 1). */
data class PontoMao(val x: Float, val y: Float)

/**
 * O que o MediaPipe viu num frame. gesto == null: sem mão ou mão sem gesto conhecido.
 * maos: os 21 pontos de cada mão; largura e altura: da imagem analisada, para desenhar por cima da câmera.
 */
data class Leitura(
    val gesto: String?,
    val confianca: Float,
    val temMao: Boolean,
    val tMs: Long,
    val maos: List<List<PontoMao>> = emptyList(),
    val largura: Int = 0,
    val altura: Int = 0,
)

/**
 * MediaPipe Gesture Recognizer em LIVE_STREAM. O resultado chega em outra thread,
 * no callback, com o horário do frame (é esse horário que vai para o filtro).
 */
class ReconhecedorGesto(context: Context, aoLer: (Leitura) -> Unit) {
    private val reconhecedor: GestureRecognizer
    private var ultimoT = -1L

    init {
        val opcoes = GestureRecognizer.GestureRecognizerOptions.builder()
            .setBaseOptions(BaseOptions.builder().setModelAssetPath("gesture_recognizer.task").build())
            .setRunningMode(RunningMode.LIVE_STREAM)
            .setResultListener { r, imagem ->
                val melhor = r.gestures().firstOrNull()?.firstOrNull()
                // o MediaPipe chama de "None" uma mão sem gesto conhecido
                val gesto = melhor?.categoryName()?.takeIf { it != "None" }
                val maos = r.landmarks().map { mao -> mao.map { PontoMao(it.x(), it.y()) } }
                aoLer(Leitura(gesto, melhor?.score() ?: 0f, maos.isNotEmpty(), r.timestampMs(), maos, imagem.width, imagem.height))
            }
            .setErrorListener { e -> Log.e(TAG, "erro no MediaPipe", e) }
            .build()
        reconhecedor = GestureRecognizer.createFromOptions(context, opcoes)
    }

    fun reconhecer(bitmap: Bitmap, tMs: Long) {
        val t = maxOf(tMs, ultimoT + 1) // o MediaPipe exige horário sempre crescente
        ultimoT = t
        try {
            reconhecedor.recognizeAsync(BitmapImageBuilder(bitmap).build(), t)
        } catch (e: IllegalStateException) {
            // um último frame pode chegar depois de fechar(), quando o app sai da tela
            Log.w(TAG, "frame ignorado: ${e.message}")
        }
    }

    fun fechar() = reconhecedor.close()
}

const val TAG = "gestos"
