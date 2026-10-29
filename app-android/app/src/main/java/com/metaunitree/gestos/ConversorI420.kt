package com.metaunitree.gestos

import android.graphics.Bitmap
import java.nio.ByteBuffer

/*
 * Quadros dos óculos -> Bitmap para o MediaPipe.
 *
 * Com compressVideo = false, o SDK dos óculos entrega cada quadro já decodificado em
 * YUV I420 (formato usado pelo conversor do app de exemplo CameraAccess 0.8.0): plano Y
 * (largura x altura bytes), depois U e V (largura/2 x altura/2 cada). Cores no padrão
 * BT.601 de faixa limitada (Y de 16 a 235), o das câmeras de vídeo.
 */

/** Converte I420 em pixels ARGB. Largura e altura têm que ser pares. */
fun i420ParaArgb(yuv: ByteArray, largura: Int, altura: Int, saida: IntArray) {
    val area = largura * altura
    val inicioU = area
    val inicioV = area + area / 4
    val meiaLargura = largura / 2
    for (lin in 0 until altura) {
        val linhaCor = (lin shr 1) * meiaLargura
        for (col in 0 until largura) {
            val y = (yuv[lin * largura + col].toInt() and 0xFF) - 16
            val i = linhaCor + (col shr 1)
            val u = (yuv[inicioU + i].toInt() and 0xFF) - 128
            val v = (yuv[inicioV + i].toInt() and 0xFF) - 128
            // coeficientes x1024: 1,164 / 1,596 / 0,391 / 0,813 / 2,018
            val y1 = 1192 * maxOf(y, 0)
            val r = (y1 + 1634 * v) shr 10
            val g = (y1 - 400 * u - 833 * v) shr 10
            val b = (y1 + 2066 * u) shr 10
            saida[lin * largura + col] =
                (0xFF shl 24) or (r.coerceIn(0, 255) shl 16) or (g.coerceIn(0, 255) shl 8) or b.coerceIn(0, 255)
        }
    }
}

/** Quadro I420 do SDK -> Bitmap novo (o MediaPipe processa em outra thread, então não reaproveita). */
fun i420ParaBitmap(dados: ByteBuffer, largura: Int, altura: Int): Bitmap? {
    if (largura <= 0 || altura <= 0 || largura % 2 != 0 || altura % 2 != 0) return null
    val tamanho = largura * altura * 3 / 2
    if (dados.remaining() < tamanho) return null
    val yuv = ByteArray(tamanho)
    dados.duplicate().get(yuv) // duplicate: não mexe na posição do buffer do SDK
    val pixels = IntArray(largura * altura)
    i420ParaArgb(yuv, largura, altura, pixels)
    return Bitmap.createBitmap(pixels, largura, altura, Bitmap.Config.ARGB_8888)
}
