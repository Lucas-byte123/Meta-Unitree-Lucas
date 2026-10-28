package com.metaunitree.gestos

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

// Os mesmos casos de mvp-gesto/tests/test_filtro.py.

private val MAPA = mapOf("Thumb_Up" to "cumprimentar", "Victory" to "sentar", "Open_Palm" to "parar")

private data class Quadro(val t: Long, val gesto: String?, val conf: Float)

/** Devolve as ações disparadas, com o horário de cada uma. */
private fun rodar(filtro: FiltroGesto, quadros: List<Quadro>): List<Pair<Long, String>> =
    quadros.mapNotNull { q -> filtro.atualizar(q.gesto, q.conf, q.t)?.let { q.t to it } }

private fun segurar(gesto: String?, de: Long, ate: Long, passo: Long = 33, conf: Float = 0.9f) =
    (de until ate step passo).map { Quadro(it, gesto, conf) }

class FiltroGestoTest {
    @Test fun disparaDepoisDeEstavel() {
        val disparos = rodar(FiltroGesto(MAPA), segurar("Thumb_Up", 0, 1000))
        assertEquals(1, disparos.size)
        val (t, acao) = disparos[0]
        assertEquals("cumprimentar", acao)
        assertTrue(t in 500 until 550)
    }

    @Test fun naoDisparaAntesDoTempo() {
        assertEquals(emptyList<Pair<Long, String>>(), rodar(FiltroGesto(MAPA), segurar("Thumb_Up", 0, 450)))
    }

    @Test fun confiancaBaixaNaoConta() {
        assertEquals(0, rodar(FiltroGesto(MAPA), segurar("Thumb_Up", 0, 2000, conf = 0.5f)).size)
    }

    @Test fun naoRepeteSemBaixarAMao() {
        assertEquals(1, rodar(FiltroGesto(MAPA), segurar("Thumb_Up", 0, 3000)).size)
    }

    @Test fun repeteDepoisDeBaixarAMao() {
        val quadros = segurar("Thumb_Up", 0, 1000) + segurar(null, 1000, 1200) + segurar("Thumb_Up", 1200, 2200)
        assertEquals(listOf("cumprimentar", "cumprimentar"), rodar(FiltroGesto(MAPA), quadros).map { it.second })
    }

    @Test fun tremidaReiniciaAContagem() {
        val quadros = segurar("Thumb_Up", 0, 400) + Quadro(400, "Victory", 0.9f) + segurar("Thumb_Up", 433, 800)
        assertEquals(0, rodar(FiltroGesto(MAPA), quadros).size)
    }

    @Test fun pararEMaisRapido() {
        val disparos = rodar(FiltroGesto(MAPA), segurar("Open_Palm", 0, 400))
        assertEquals(1, disparos.size)
        val (t, acao) = disparos[0]
        assertEquals("parar", acao)
        assertTrue(t < 250)
    }

    @Test fun pararAceitaConfiancaMaisBaixa() {
        // 0,6: abaixo do mínimo dos truques (0,65), acima do do parar (0,55)
        assertEquals(listOf("parar"), rodar(FiltroGesto(MAPA), segurar("Open_Palm", 0, 400, conf = 0.6f)).map { it.second })
        assertEquals(0, rodar(FiltroGesto(MAPA), segurar("Thumb_Up", 0, 2000, conf = 0.6f)).size)
    }

    @Test fun pararAbaixoDoMinimoNaoDispara() {
        assertEquals(0, rodar(FiltroGesto(MAPA), segurar("Open_Palm", 0, 2000, conf = 0.5f)).size)
    }

    @Test fun gestoForaDoMapaNaoDispara() {
        assertEquals(0, rodar(FiltroGesto(MAPA), segurar("ILoveYou", 0, 2000)).size)
    }

    @Test fun trocarDeGestoDisparaONovo() {
        val quadros = segurar("Thumb_Up", 0, 800) + segurar("Victory", 800, 1600)
        assertEquals(listOf("cumprimentar", "sentar"), rodar(FiltroGesto(MAPA), quadros).map { it.second })
    }

    @Test fun progresso() {
        val f = FiltroGesto(MAPA)
        f.atualizar("Thumb_Up", 0.9f, 0)
        assertEquals(0.5f, f.progresso(250), 1e-6f)
        f.atualizar("Thumb_Up", 0.9f, 600)
        assertEquals(0f, f.progresso(600), 0f) // já disparou
    }
}
