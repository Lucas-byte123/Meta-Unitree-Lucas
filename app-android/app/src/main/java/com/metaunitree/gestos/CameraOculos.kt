package com.metaunitree.gestos

import android.content.Context
import android.graphics.Bitmap
import android.os.SystemClock
import android.util.Log
import com.meta.wearable.dat.camera.Camera
import com.meta.wearable.dat.camera.addCamera
import com.meta.wearable.dat.camera.types.StreamConfiguration
import com.meta.wearable.dat.camera.types.VideoQuality
import com.meta.wearable.dat.core.Wearables
import com.meta.wearable.dat.core.selectors.AutoDeviceSelector
import com.meta.wearable.dat.core.session.DeviceSession
import com.meta.wearable.dat.core.session.DeviceSessionState
import com.meta.wearable.dat.core.types.Permission
import com.meta.wearable.dat.core.types.PermissionStatus
import com.meta.wearable.dat.core.types.RegistrationState
import com.meta.wearable.dat.mockdevice.MockDeviceKit
import com.meta.wearable.dat.mockdevice.api.GlassesModel
import com.meta.wearable.dat.mockdevice.api.MockDeviceKitConfig
import com.meta.wearable.dat.mockdevice.api.camera.CameraFacing
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeoutOrNull

/**
 * Câmera dos óculos Ray-Ban Meta pelo SDK Meta DAT 1.0.1.
 *
 * Caminho: registro no app Meta AI -> permissão de câmera -> sessão com os óculos ->
 * câmera -> stream de quadros I420 -> Bitmap. Com [falsos] = true, usa o MockDeviceKit
 * do SDK: óculos de mentira, já registrados e com permissão, que transmitem a câmera
 * traseira do celular. Serve para testar este caminho todo sem os óculos.
 *
 * [pedirPermissao] abre o pedido de permissão no app Meta AI (precisa da Activity).
 * [aoMudarEstado] recebe uma frase curta para mostrar na tela.
 */
class CameraOculos(
    private val context: Context,
    private val escopo: CoroutineScope,
    private val falsos: Boolean,
    private val pedirPermissao: suspend (Permission) -> PermissionStatus,
    private val aoMudarEstado: (String) -> Unit,
) : FonteDeFrames {
    private var sessao: DeviceSession? = null
    @Volatile private var formatoAnotado = false
    private var camera: Camera? = null
    private val tarefas = mutableListOf<Job>()

    override fun iniciar(aoChegarFrame: (bitmap: Bitmap, tMs: Long) -> Unit) {
        parar()
        if (falsos) prepararOculosFalsos()
        tarefas += escopo.launch {
            // o estado do registro pode demorar um pouco para chegar (principalmente nos falsos)
            val registrado = withTimeoutOrNull(3000) {
                Wearables.registrationState.first { it == RegistrationState.REGISTERED }
            } != null
            if (!registrado) {
                aoMudarEstado("óculos: app não registrado no Meta AI (toque em Registrar)")
                return@launch
            }
            val status = Wearables.checkPermissionStatus(Permission.CAMERA).getOrNull()
            val permitido = status == PermissionStatus.Granted || pedirPermissao(Permission.CAMERA) == PermissionStatus.Granted
            if (!permitido) {
                aoMudarEstado("óculos: sem permissão de câmera no Meta AI")
                return@launch
            }
            abrirSessao(aoChegarFrame)
        }
    }

    private fun abrirSessao(aoChegarFrame: (Bitmap, Long) -> Unit) {
        Wearables.createSession(AutoDeviceSelector())
            .onSuccess { s ->
                sessao = s
                // acompanhar antes de start(), para não perder nenhuma transição
                tarefas += escopo.launch { s.errors.collect { e -> aoMudarEstado("óculos: ${e.description}") } }
                tarefas += escopo.launch {
                    s.state.collect { estado ->
                        aoMudarEstado("óculos: sessão $estado")
                        when (estado) {
                            DeviceSessionState.STARTED -> if (camera == null) abrirCamera(s, aoChegarFrame)
                            DeviceSessionState.STOPPED -> camera = null
                            else -> {}
                        }
                    }
                }
                s.start()
            }
            .onFailure { e, _ -> aoMudarEstado("óculos: ${e.description}") }
    }

    private fun abrirCamera(s: DeviceSession, aoChegarFrame: (Bitmap, Long) -> Unit) {
        // LOW = 360x640: basta para a mão e alivia o Bluetooth. 15 fps é o que o Android
        // entrega pelo Bluetooth (docs/pesquisa.md). compressVideo = false: quadros em I420.
        val config = StreamConfiguration(videoQuality = VideoQuality.LOW, frameRate = 15, compressVideo = false)
        s.addCamera(config)
            .onSuccess { c ->
                camera = c
                val stream = c.stream
                tarefas += escopo.launch { stream.state.collect { aoMudarEstado("óculos: stream $it") } }
                tarefas += escopo.launch { stream.errorStream.collect { aoMudarEstado("óculos: ${it.description}") } }
                tarefas += escopo.launch(Dispatchers.Default) {
                    stream.videoStream.collect { q ->
                        if (q.isCompressed) return@collect
                        val t = SystemClock.uptimeMillis()
                        if (!formatoAnotado) {
                            // I420 sem sobras ocupa largura x altura x 1,5 bytes; mais que isso indica linhas com folga
                            Log.i(TAG, "1º quadro dos óculos: ${q.width}x${q.height}, ${q.buffer.remaining()} bytes " +
                                "(I420 exato: ${q.width * q.height * 3 / 2})")
                            formatoAnotado = true
                        }
                        val bitmap = i420ParaBitmap(q.buffer, q.width, q.height)
                        if (bitmap == null) {
                            Log.w(TAG, "quadro dos óculos fora do I420 esperado: ${q.width}x${q.height}, ${q.buffer.remaining()} bytes")
                        } else {
                            aoChegarFrame(bitmap, t)
                        }
                    }
                }
                stream.start().onFailure { e, _ -> aoMudarEstado("óculos: ${e.description}") }
            }
            .onFailure { e, _ -> aoMudarEstado("óculos: ${e.description}") }
    }

    /** Óculos de mentira do SDK: registrados, com permissão, ligados, no rosto, com a câmera traseira. */
    private fun prepararOculosFalsos() {
        val kit = MockDeviceKit.getInstance(context)
        if (!kit.isEnabled) kit.enable(MockDeviceKitConfig(true, true))
        if (kit.pairedDevices.isNotEmpty()) return
        kit.pairGlasses(GlassesModel.RAYBAN_META)
            .onSuccess { oculos ->
                oculos.powerOn()
                oculos.unfold()
                oculos.don()
                oculos.services.camera.setCameraFeed(CameraFacing.BACK)
            }
            .onFailure { e, _ -> aoMudarEstado("óculos falsos: ${e.description}") }
    }

    companion object {
        /** Desliga os óculos falsos (eles usam a câmera traseira e disputam com o CameraX). */
        fun desligarFalsos(context: Context) {
            val kit = MockDeviceKit.getInstance(context)
            if (kit.isEnabled) kit.disable()
        }
    }

    override fun parar() {
        tarefas.forEach { it.cancel() }
        tarefas.clear()
        // parar a câmera solta o recurso; sem isso, o próximo addCamera falha
        camera?.stop()
        camera = null
        sessao?.stop()
        sessao = null
    }
}
