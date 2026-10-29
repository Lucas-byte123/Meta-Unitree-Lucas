package com.metaunitree.gestos

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ConversorI420Test {
    /** Quadro 2x2 com uma cor só (um único par U, V). */
    private fun cor(y: Int, u: Int, v: Int): Triple<Int, Int, Int> {
        val saida = IntArray(4)
        i420ParaArgb(byteArrayOf(y.toByte(), y.toByte(), y.toByte(), y.toByte(), u.toByte(), v.toByte()), 2, 2, saida)
        val p = saida[0]
        assertEquals(0xFF, p ushr 24) // opaco
        return Triple((p shr 16) and 0xFF, (p shr 8) and 0xFF, p and 0xFF)
    }

    private fun perto(esperado: Triple<Int, Int, Int>, obtido: Triple<Int, Int, Int>) {
        val ok = listOf(esperado.first to obtido.first, esperado.second to obtido.second, esperado.third to obtido.third)
            .all { (e, o) -> kotlin.math.abs(e - o) <= 3 }
        assertTrue("esperado $esperado, veio $obtido", ok)
    }

    @Test fun pretoBrancoECinza() {
        perto(Triple(0, 0, 0), cor(16, 128, 128))
        perto(Triple(255, 255, 255), cor(235, 128, 128))
        perto(Triple(128, 128, 128), cor(126, 128, 128))
    }

    @Test fun coresPrimarias() {
        // valores BT.601 de faixa limitada para vermelho, verde e azul puros
        perto(Triple(255, 0, 0), cor(81, 90, 240))
        perto(Triple(0, 255, 0), cor(145, 54, 34))
        perto(Triple(0, 0, 255), cor(41, 240, 110))
    }

    @Test fun cadaBlocoDe2x2UsaSeuProprioUV() {
        // 4x2: dois blocos 2x2; o da esquerda vermelho, o da direita azul.
        // Se U e V estivessem trocados (NV12/NV21 ou YV12), as cores sairiam trocadas.
        val y = byteArrayOf(81, 81, 41, 41, 81, 81, 41, 41)
        val u = byteArrayOf(90, 240.toByte())
        val v = byteArrayOf(240.toByte(), 110)
        val saida = IntArray(8)
        i420ParaArgb(y + u + v, 4, 2, saida)
        for (lin in 0 until 2) {
            assertTrue("esquerda vermelha", (saida[lin * 4] shr 16 and 0xFF) > 240)
            assertTrue("direita azul", (saida[lin * 4 + 3] and 0xFF) > 240)
        }
    }
}
