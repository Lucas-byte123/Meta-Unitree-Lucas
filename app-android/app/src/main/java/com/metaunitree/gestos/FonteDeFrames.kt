package com.metaunitree.gestos

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Matrix
import android.os.SystemClock
import android.util.Size
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.Preview
import androidx.camera.core.resolutionselector.ResolutionSelector
import androidx.camera.core.resolutionselector.ResolutionStrategy
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleOwner
import java.util.concurrent.Executors

/**
 * De onde vêm os frames. Hoje é a câmera do celular; quando os óculos funcionarem,
 * entra uma CameraOculos (Meta DAT) e o resto do app não muda.
 */
interface FonteDeFrames {
    /** Começa a entregar frames já na orientação certa, com o horário em ms (SystemClock.uptimeMillis). */
    fun iniciar(aoChegarFrame: (bitmap: Bitmap, tMs: Long) -> Unit)
    fun parar()
}

/** Câmera do celular pelo CameraX. A traseira, apontada para a frente, simula a visão dos óculos. */
class CameraCelular(
    private val context: Context,
    private val dono: LifecycleOwner,
    private val preview: PreviewView,
) : FonteDeFrames {
    var traseira = true
    private val executor = Executors.newSingleThreadExecutor()
    private var provedor: ProcessCameraProvider? = null

    override fun iniciar(aoChegarFrame: (bitmap: Bitmap, tMs: Long) -> Unit) {
        val futuro = ProcessCameraProvider.getInstance(context)
        futuro.addListener({
            val p = futuro.get()
            provedor = p
            val visualizacao = Preview.Builder().build()
            visualizacao.setSurfaceProvider(preview.surfaceProvider)
            // 640x480 basta para a mão; os óculos vão entregar algo parecido (~15 fps)
            val resolucao = ResolutionSelector.Builder()
                .setResolutionStrategy(
                    ResolutionStrategy(Size(640, 480), ResolutionStrategy.FALLBACK_RULE_CLOSEST_HIGHER_THEN_LOWER)
                )
                .build()
            val analise = ImageAnalysis.Builder()
                .setResolutionSelector(resolucao)
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .setOutputImageFormat(ImageAnalysis.OUTPUT_IMAGE_FORMAT_RGBA_8888)
                .build()
            analise.setAnalyzer(executor) { imagem ->
                val t = SystemClock.uptimeMillis()
                val bitmap = imagem.use { girar(it.toBitmap(), it.imageInfo.rotationDegrees) }
                aoChegarFrame(bitmap, t)
            }
            val seletor = if (traseira) CameraSelector.DEFAULT_BACK_CAMERA else CameraSelector.DEFAULT_FRONT_CAMERA
            p.unbindAll()
            p.bindToLifecycle(dono, seletor, visualizacao, analise)
        }, ContextCompat.getMainExecutor(context))
    }

    override fun parar() {
        provedor?.unbindAll()
    }

    // sem girar, a mão chega deitada e o reconhecimento cai
    private fun girar(bitmap: Bitmap, graus: Int): Bitmap {
        if (graus == 0) return bitmap
        val m = Matrix().apply { postRotate(graus.toFloat()) }
        return Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, m, true)
    }
}
