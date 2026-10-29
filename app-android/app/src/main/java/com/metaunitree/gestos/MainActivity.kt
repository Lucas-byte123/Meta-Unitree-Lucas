package com.metaunitree.gestos

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.os.SystemClock
import android.util.Log
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.view.PreviewView
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.update

private val VERDE = Color(0xFF50C850)
private val VERMELHO = Color(0xFFE63C3C)
private val AMARELO = Color(0xFFFFC800)

/** Tudo que a tela mostra. */
data class EstadoTela(
    val gesto: String = "sem mão",
    val acaoDoGesto: String? = null,
    val gestoValido: Boolean = false,
    val progresso: Float = 0f,
    val ultima: String = "-",
    val corUltima: Color = Color.White,
    val ponte: String = "desconectada",
    val fps: Int = 0,
    val maos: List<List<PontoMao>> = emptyList(),
    val larguraImagem: Int = 0,
    val alturaImagem: Int = 0,
    val espelhar: Boolean = false, // a pré-visualização da câmera frontal é espelhada; a imagem analisada, não
)

class MainActivity : ComponentActivity() {
    private val estado = MutableStateFlow(EstadoTela())
    private lateinit var preview: PreviewView
    private lateinit var camera: CameraCelular
    private lateinit var cliente: ClientePonte
    private var reconhecedor: ReconhecedorGesto? = null
    private val prefs by lazy { getSharedPreferences("gestos", MODE_PRIVATE) }
    private val registro by lazy { RegistroCsv(this) }

    @Volatile private var filtro = FiltroGesto(MAPAS.getValue("go2"))
    private var ultimoHeartbeat = 0L
    private var quadrosNoSegundo = 0
    private var inicioDoSegundo = 0L

    private val pedirCamera = registerForActivityResult(ActivityResultContracts.RequestPermission()) { ok ->
        if (ok) iniciar() else mostrar("sem permissão de câmera", VERMELHO)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        filtro = FiltroGesto(MAPAS.getValue(robo()))
        preview = PreviewView(this)
        camera = CameraCelular(this, this, preview)
        cliente = ClientePonte(
            aoMudarEstado = { e -> estado.update { it.copy(ponte = e) } },
            aoResponder = { r ->
                Log.i(TAG, "ponte: $r")
                if (r.ok) mostrar("${r.acao}: ok", VERDE) else mostrar("recusado: ${r.erro}", VERMELHO)
            },
        )
        setContent {
            MaterialTheme(colorScheme = darkColorScheme()) {
                val e by estado.collectAsStateWithLifecycle()
                Tela(
                    e = e,
                    preview = preview,
                    enderecoInicial = endereco(),
                    roboInicial = robo(),
                    aoConectar = { url ->
                        prefs.edit().putString("endereco", url).apply()
                        cliente.conectar(url)
                    },
                    aoTrocarRobo = { r ->
                        prefs.edit().putString("robo", r).apply()
                        filtro = FiltroGesto(MAPAS.getValue(r))
                    },
                    aoTrocarCamera = {
                        camera.traseira = !camera.traseira
                        if (reconhecedor != null) camera.iniciar(::aoChegarFrame)
                    },
                    aoParar = {
                        // não depende de gesto: manda parar direto
                        if (cliente.acao("parar")) mostrar("parar enviado", AMARELO)
                        else mostrar("parar: sem conexão com a ponte", VERMELHO)
                    },
                )
            }
        }
    }

    override fun onStart() {
        super.onStart()
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
            iniciar()
        } else {
            pedirCamera.launch(Manifest.permission.CAMERA)
        }
    }

    // App fora da tela não comanda nada: fecha a conexão e a ponte para o robô.
    override fun onStop() {
        super.onStop()
        camera.parar()
        cliente.desconectar()
        reconhecedor?.fechar()
        reconhecedor = null
        registro.fechar()
    }

    private fun iniciar() {
        if (reconhecedor != null) return
        registro.abrir()
        reconhecedor = ReconhecedorGesto(this, ::aoLer)
        camera.iniciar(::aoChegarFrame)
        cliente.conectar(endereco())
    }

    private fun aoChegarFrame(bitmap: android.graphics.Bitmap, tMs: Long) {
        reconhecedor?.reconhecer(bitmap, tMs)
    }

    /** Roda na thread do MediaPipe, uma vez por frame processado. */
    private fun aoLer(l: Leitura) {
        val f = filtro
        val acao = f.atualizar(l.gesto, l.confianca, l.tMs)
        registro.escrever(l, acao)
        if (acao != null) {
            Log.i(TAG, "${l.gesto} -> $acao")
            if (!cliente.acao(acao)) mostrar("$acao (sem ponte)", AMARELO)
        }
        // heartbeat sai daqui, do processamento dos frames: se a câmera ou o MediaPipe
        // travar, ele para junto e a ponte para o robô
        val agora = SystemClock.uptimeMillis()
        if (agora - ultimoHeartbeat >= HEARTBEAT_MS) {
            cliente.heartbeat()
            ultimoHeartbeat = agora
        }

        quadrosNoSegundo++
        val fps = if (agora - inicioDoSegundo >= 1000) {
            val v = (quadrosNoSegundo * 1000 / (agora - inicioDoSegundo).coerceAtLeast(1)).toInt()
            quadrosNoSegundo = 0
            inicioDoSegundo = agora
            v
        } else null

        val valido = f.vale(l.gesto, l.confianca)
        val texto = when {
            l.gesto != null -> "%s %.2f".format(l.gesto, l.confianca)
            l.temMao -> "mão sem gesto"
            else -> "sem mão"
        }
        estado.update {
            it.copy(
                gesto = texto,
                acaoDoGesto = l.gesto?.let { g -> f.mapa[g] },
                gestoValido = valido,
                progresso = f.progresso(l.tMs),
                fps = fps ?: it.fps,
                maos = l.maos,
                larguraImagem = l.largura,
                alturaImagem = l.altura,
                espelhar = !camera.traseira,
            )
        }
    }

    private fun mostrar(texto: String, cor: Color) = estado.update { it.copy(ultima = texto, corUltima = cor) }

    // padrão: localhost, que chega no laptop pelo cabo com `adb reverse tcp:8765 tcp:8765`
    private fun endereco() = prefs.getString("endereco", "ws://localhost:8765")!!
    private fun robo() = prefs.getString("robo", "go2")!!

    companion object {
        const val HEARTBEAT_MS = 100L
    }
}

@Composable
private fun Tela(
    e: EstadoTela,
    preview: PreviewView,
    enderecoInicial: String,
    roboInicial: String,
    aoConectar: (String) -> Unit,
    aoTrocarRobo: (String) -> Unit,
    aoTrocarCamera: () -> Unit,
    aoParar: () -> Unit,
) {
    var endereco by remember { mutableStateOf(enderecoInicial) }
    var robo by remember { mutableStateOf(roboInicial) }

    Box(Modifier.fillMaxSize().background(Color.Black)) {
        AndroidView(factory = { preview }, modifier = Modifier.fillMaxSize())
        Esqueleto(e, cor = if (e.gestoValido && e.acaoDoGesto != null) VERDE else AMARELO)

        Column(
            Modifier.fillMaxWidth().background(Color(0xAA000000)).systemBarsPadding().padding(12.dp)
        ) {
            val linha = e.gesto + (e.acaoDoGesto?.let { "  →  $it" } ?: "")
            Text(
                linha,
                color = if (e.gestoValido && e.acaoDoGesto != null) VERDE else Color.White,
                fontSize = 22.sp,
                fontWeight = FontWeight.Bold,
            )
            Spacer(Modifier.height(6.dp))
            LinearProgressIndicator(
                progress = { e.progresso },
                modifier = Modifier.fillMaxWidth().height(8.dp),
                color = VERDE,
            )
            Spacer(Modifier.height(6.dp))
            Text("última: ${e.ultima}", color = e.corUltima, fontSize = 16.sp)
            Text("ponte: ${e.ponte}   ${e.fps} fps", color = Color.White, fontSize = 14.sp)
        }

        Column(
            Modifier.align(Alignment.BottomCenter).fillMaxWidth().background(Color(0xAA000000))
                .systemBarsPadding().imePadding().padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                OutlinedTextField(
                    value = endereco,
                    onValueChange = { endereco = it },
                    label = { Text("ponte") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
                    colors = TextFieldDefaults.colors(
                        focusedContainerColor = Color.Transparent,
                        unfocusedContainerColor = Color.Transparent,
                    ),
                    modifier = Modifier.weight(1f),
                )
                Spacer(Modifier.width(8.dp))
                Button(onClick = { aoConectar(endereco.trim()) }) { Text("Conectar") }
            }
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                for (r in MAPAS.keys) {
                    FilterChip(
                        selected = robo == r,
                        onClick = { robo = r; aoTrocarRobo(r) },
                        label = { Text(r) },
                    )
                }
                Spacer(Modifier.weight(1f))
                OutlinedButton(onClick = aoTrocarCamera) { Text("Trocar câmera") }
            }
            Button(
                onClick = aoParar,
                colors = ButtonDefaults.buttonColors(containerColor = VERMELHO, contentColor = Color.White),
                modifier = Modifier.fillMaxWidth().height(72.dp),
            ) {
                Text("PARAR", fontSize = 28.sp, fontWeight = FontWeight.Bold)
            }
        }
    }
}

// Ligações entre os 21 pontos da mão do MediaPipe (punho = 0, pontas dos dedos = 4, 8, 12, 16, 20).
private val LIGACOES_MAO = listOf(
    0 to 1, 1 to 2, 2 to 3, 3 to 4,
    0 to 5, 5 to 6, 6 to 7, 7 to 8,
    5 to 9, 9 to 10, 10 to 11, 11 to 12,
    9 to 13, 13 to 14, 14 to 15, 15 to 16,
    13 to 17, 17 to 18, 18 to 19, 19 to 20, 0 to 17,
)

/** Desenha a mão que o MediaPipe vê, por cima da câmera. Verde quando o gesto vale. */
@Composable
private fun Esqueleto(e: EstadoTela, cor: Color) {
    if (e.maos.isEmpty() || e.larguraImagem == 0) return
    Canvas(Modifier.fillMaxSize()) {
        // a pré-visualização preenche a tela cortando as bordas (FILL_CENTER); a mesma conta aqui
        val escala = maxOf(size.width / e.larguraImagem, size.height / e.alturaImagem)
        val dx = (size.width - e.larguraImagem * escala) / 2
        val dy = (size.height - e.alturaImagem * escala) / 2
        fun ponto(p: PontoMao): Offset {
            val x = p.x * e.larguraImagem * escala + dx
            return Offset(if (e.espelhar) size.width - x else x, p.y * e.alturaImagem * escala + dy)
        }
        for (mao in e.maos) {
            if (mao.size < 21) continue
            for ((a, b) in LIGACOES_MAO) drawLine(cor, ponto(mao[a]), ponto(mao[b]), strokeWidth = 6f)
            for (p in mao) drawCircle(Color.White, radius = 9f, center = ponto(p))
        }
    }
}
