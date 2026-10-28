package com.metaunitree.gestos

import android.util.Log
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONObject
import java.util.UUID

/** Resposta (ack) da ponte. Erros possíveis: "ocupado", "em movimento", "ação não permitida: ...", "JSON inválido". */
data class Ack(val ok: Boolean, val acao: String?, val erro: String?)

/**
 * WebSocket com a ponte (protocolo no comentário do topo de mvp-gesto/ponte.py).
 *
 * Segurança: a ponte para o robô se ficar 300 ms sem heartbeat ou se a conexão cair.
 * Por isso quem chama heartbeat() é o processamento dos frames (se a câmera travar,
 * o heartbeat para junto), e o app chama desconectar() quando sai de cena.
 */
class ClientePonte(
    private val aoMudarEstado: (String) -> Unit,
    private val aoResponder: (Ack) -> Unit,
) {
    private val http = OkHttpClient()
    @Volatile private var ws: WebSocket? = null
    @Volatile private var geracao = 0 // ignora eventos de uma conexão antiga
    @Volatile var conectado = false
        private set

    fun conectar(url: String) {
        desconectar()
        aoMudarEstado("conectando")
        val pedido = try {
            Request.Builder().url(url).build()
        } catch (e: IllegalArgumentException) {
            aoMudarEstado("endereço inválido")
            return
        }
        val minha = ++geracao
        ws = http.newWebSocket(pedido, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                if (minha != geracao) return
                conectado = true
                aoMudarEstado("conectada")
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                if (minha != geracao) return
                try {
                    val r = JSONObject(text)
                    aoResponder(Ack(r.optBoolean("ok"), r.optString("acao").ifEmpty { null }, r.optString("erro").ifEmpty { null }))
                } catch (e: Exception) {
                    Log.w(TAG, "resposta da ponte não é JSON: $text")
                }
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                if (minha != geracao) return
                conectado = false
                aoMudarEstado("desconectada")
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                if (minha != geracao) return
                conectado = false
                aoMudarEstado("sem conexão (${t.message ?: t.javaClass.simpleName})")
            }
        })
    }

    fun desconectar() {
        val atual = ws ?: return
        geracao++
        ws = null
        conectado = false
        atual.close(1000, "app saiu")
        aoMudarEstado("desconectada")
    }

    fun heartbeat() {
        if (conectado) ws?.send("""{"tipo":"heartbeat"}""")
    }

    /** Manda uma ação. Devolve false se não há conexão. */
    fun acao(acao: String): Boolean {
        if (!conectado) return false
        val msg = JSONObject().put("tipo", "acao").put("acao", acao).put("id", UUID.randomUUID().toString().take(8))
        return ws?.send(msg.toString()) ?: false
    }
}
