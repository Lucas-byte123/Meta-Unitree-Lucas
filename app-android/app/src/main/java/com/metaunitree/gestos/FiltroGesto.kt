package com.metaunitree.gestos

/*
 * Filtro anti-disparo: transforma o gesto reconhecido em cada frame numa ação.
 *
 * Tradução de mvp-gesto/filtro.py. As regras e os testes têm que continuar iguais
 * aos do Python (ver AGENTS.md):
 * - confiança abaixo do mínimo conta como "sem gesto"; o mínimo do "parar" é mais
 *   baixo, porque um parar à toa só para o robô e um parar perdido é perigoso;
 * - o gesto precisa ficar estável por um tempo antes de valer (parar é mais rápido);
 * - depois de disparar, o mesmo gesto só vale de novo depois de baixar a mão
 *   (ou trocar de gesto).
 */

// Medido em 28/10/2026 no celular: Thumb_Up e Open_Palm ficam entre 0,6 e 0,7,
// então 0,7 quase nunca disparava.
const val CONFIANCA_MIN = 0.65f
const val CONFIANCA_MIN_PARAR = 0.55f
const val ESTAVEL_MS = 500L        // gesto parado por ~0,5 s antes de valer
const val ESTAVEL_PARAR_MS = 200L  // "parar" tem prioridade: vale mais rápido

class FiltroGesto(
    val mapa: Map<String, String>,
    private val confiancaMin: Float = CONFIANCA_MIN,
    private val confiancaMinParar: Float = CONFIANCA_MIN_PARAR,
    private val estavelMs: Long = ESTAVEL_MS,
    private val estavelPararMs: Long = ESTAVEL_PARAR_MS,
) {
    private var atual: String? = null     // gesto visto agora (já filtrado pela confiança)
    private var desdeMs = 0L              // desde quando o gesto atual está estável
    private var disparado: String? = null // último gesto que virou ação

    /** Recebe o gesto de um frame e devolve a ação a disparar, ou null. */
    fun atualizar(gesto: String?, confianca: Float, tMs: Long): String? {
        val g = if (vale(gesto, confianca)) gesto else null
        if (g != atual) {
            atual = g
            desdeMs = tMs
        }
        if (g == null) {
            disparado = null // mão baixou: o próximo gesto pode disparar
            return null
        }
        val acao = mapa[g] ?: return null
        if (g == disparado) return null
        if (tMs - desdeMs >= espera(acao)) {
            disparado = g
            return acao
        }
        return null
    }

    /** Se o gesto passa da confiança mínima (a do parar é mais baixa). */
    fun vale(gesto: String?, confianca: Float): Boolean {
        if (gesto == null) return false
        val minimo = if (mapa[gesto] == "parar") confiancaMinParar else confiancaMin
        return confianca >= minimo
    }

    /** Fração (0 a 1) do tempo de estabilidade já cumprido pelo gesto atual. */
    fun progresso(tMs: Long): Float {
        val g = atual ?: return 0f
        val acao = mapa[g] ?: return 0f
        if (g == disparado) return 0f
        return minOf(1f, (tMs - desdeMs).toFloat() / espera(acao))
    }

    private fun espera(acao: String) = if (acao == "parar") estavelPararMs else estavelMs
}

// Gestos prontos do MediaPipe: Closed_Fist, Open_Palm, Pointing_Up,
// Thumb_Down, Thumb_Up, Victory, ILoveYou. Igual ao MAPA de gesto_webcam.py.
val MAPAS: Map<String, Map<String, String>> = mapOf(
    "go2" to mapOf(
        "Thumb_Up" to "cumprimentar",
        "Victory" to "sentar",
        "Pointing_Up" to "levantar",
        "Open_Palm" to "parar",
    ),
    "g1" to mapOf(
        "Thumb_Up" to "cumprimentar",
        "Victory" to "high_five",
        "ILoveYou" to "palmas",
        "Open_Palm" to "parar",
    ),
)
