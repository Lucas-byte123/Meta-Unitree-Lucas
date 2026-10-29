# AGENTS.md

Instruções para assistentes de código (Claude Code, Codex, Cursor...) neste repositório. Vale também para pessoas novas no projeto.

## O projeto

Controlar os robôs Unitree **Go2 EDU** (primeiro) e **G1 EDU** (depois) com gestos de mão vistos pela câmera dos óculos **Ray-Ban Meta Gen 2**. Meta futura: apontar para um ponto no chão e o Go2 ir até lá.

```
óculos --Bluetooth (Meta DAT SDK)--> celular Android (MediaPipe + filtro)
       --Wi-Fi, WebSocket JSON--> ponte.py (Python) --WebRTC ou DDS--> robô
```

Antes de mudar algo grande, leia: [`docs/plano.md`](docs/plano.md) (semanas e checkpoints), [`docs/arquitetura.md`](docs/arquitetura.md) (como e por quê) e [`docs/pesquisa.md`](docs/pesquisa.md) (SDKs, fontes). O estado atual de cada parte está no [README](README.md#estado).

## Mapa do repositório

| Caminho | O que é |
|---|---|
| `mvp-gesto/ponte.py` | Servidor WebSocket; valida comandos, limita velocidade, para o robô. Backends `mock`, `go2`, `g1` (falta `go2-webrtc`). O comentário do topo é a definição do protocolo. |
| `mvp-gesto/filtro.py` | Filtro anti-disparo: gesto de cada frame -> ação. Sem dependências. |
| `mvp-gesto/gesto_webcam.py` | MediaPipe na webcam ou em vídeo -> filtro -> ponte. Referência para o app Android. |
| `mvp-gesto/teclado.py` | Cliente de teste: manda ações digitadas. |
| `mvp-gesto/tests/` | `unittest` do filtro e da ponte, sem robô e sem câmera. |
| `app-android/` | App Android (ainda não existe). Especificação em [`docs/guia-app-android.md`](docs/guia-app-android.md). |

## App Android (`app-android/`)

- Mesma configuração do app de exemplo do SDK dos óculos: `minSdk 31`, `compileSdk 36`, JDK 17, Kotlin 2.2, Compose.
- SDK dos óculos (Meta DAT) 1.0.1, no Maven Central, sem token. Para consultar a documentação dele, use o MCP `https://mcp.developer.meta.com/wearables` (público, sem autenticação) em vez de adivinhar a API.
- Testar com o celular no cabo: `adb reverse tcp:8765 tcp:8765` e a ponte em `ws://localhost:8765`.

## Comandos

Tudo do Python roda **de dentro de `mvp-gesto/`** e com o ambiente virtual ativo. Use **Python 3.11**: o MediaPipe não tem versão para o 3.14, e o `python3` do sistema pode ser o 3.14.

```
cd mvp-gesto
python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python -m unittest                  # 27 testes, ~3 s; rodar antes de todo commit que mexe em Python
python ponte.py --robo mock         # terminal 1
python gesto_webcam.py              # terminal 2 (webcam)
python gesto_webcam.py --video x.mp4 --ponte nenhuma --log x.csv   # medir em vídeo gravado
python teclado.py                   # no lugar da webcam: frente, parar, mover 0.2 0 0 ...
```

O modelo `gesture_recognizer.task` é baixado sozinho na primeira execução (fica fora do git). Se o `pip` falhar com `SSLEOFError` no `files.pythonhosted.org`, é a rede ou o sandbox, não o `requirements.txt`: tente de novo fora do sandbox.

## Regras de segurança (não negociáveis)

O código comanda robôs de verdade, de 15 kg (Go2) e 35 kg (G1).

- **Nunca rode a ponte com `--robo go2`, `--robo g1` ou `go2-webrtc`.** Só `--robo mock`. Testes com robô são feitos por pessoas, com uma segunda pessoa no controle físico.
- **Não afrouxe os limites da ponte** sem pedido explícito: `VEL_MAX_LINEAR` 0,3 m/s, `VEL_MAX_GIRO` 0,6 rad/s, `DURACAO_MOVIMENTO_S` 1 s, `HEARTBEAT_TIMEOUT_S` 0,3 s.
- **`parar` nunca espera:** sem cooldown, sem fila na frente, sempre o último comando a chegar no robô.
- **Desconexão ou heartbeat perdido = parar.** Qualquer cliente novo (o app, por exemplo) manda heartbeat a cada 100 ms a partir do processamento de frames, e fecha a conexão quando sai de cena.
- **Lista fechada de ações.** Nada de comando livre vindo do celular, de LLM ou de voz sem passar pela validação da ponte.
- **G1: nunca `Damp`** (tira o torque e o humanoide cai). Primeiros testes sempre no pórtico.
- A ponte **não roda no celular**: o vigia de segurança precisa sobreviver se o celular cair.

## Decisões já tomadas (não reabrir sem motivo novo)

- **Sem simulação.** O `unitree_mujoco` não tem os comandos de alto nível (`Move`, `Hello`...) e não há política de locomoção pronta para o Go2. Desenvolve-se em `mock` e testa-se no robô real.
- **Dois caminhos até o robô:** A = ponte no laptop + WebRTC (começar por ele); B = ponte no Jetson do robô + SDK oficial (destino final). O Jetson do Go2 EDU não tem Wi-Fi: precisa de adaptador USB.
- **A ponte fica em Python**; o celular só reconhece e manda comandos.
- **MediaPipe fixado em 0.10.35** (a 1.x não foi testada).

## O que precisa ficar igual em vários lugares

Ao mudar um destes, atualize os outros no mesmo commit:

| O quê | Onde |
|---|---|
| Protocolo JSON | comentário do topo de `ponte.py`, `docs/arquitetura.md`, `docs/guia-app-android.md`, app Android |
| Mapa gesto -> ação | `MAPA` em `gesto_webcam.py`, `mvp-gesto/README.md`, `docs/guia-app-android.md`, app Android |
| Regras do filtro (0,7 / 500 ms / 200 ms) | `filtro.py` e sua versão em Kotlin, com os mesmos casos de teste |
| Estado do projeto | tabela "Estado" do `README.md` e do `mvp-gesto/README.md` |

## Convenções

- **Tudo em português:** nomes no código, comentários, docs, mensagens de commit. Os nomes das categorias do MediaPipe (`Thumb_Up`...) e das APIs da Unitree (`StopMove`...) ficam como são.
- Texto do `cv2.putText` **sem acentos** (o OpenCV não desenha fora do ASCII).
- Docs: frases curtas, tabelas, datas absolutas (dd/mm/aaaa), fonte com link para cada afirmação sobre hardware ou SDK. O que é dedução ou não foi testado aparece marcado como tal.
- Testes com `unittest` da biblioteca padrão; o `RoboMock` guarda as chamadas em `chamadas` para os testes conferirem.
- Git: trabalhar em branch, nunca commitar direto no `main`; PR para o `main`.
- Afirmar só o que foi verificado: "testado em mock" e "testado no robô" são coisas diferentes, e a doc deixa claro qual é qual.
