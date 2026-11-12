# Pendências

> Anotadas em 05/11/2026, ao fim da sessão em que os gestos nos óculos comandaram o Go2 real pela primeira vez.

## Onde paramos

O caminho completo funcionou no robô real em 05/11/2026:

```
Óculos Ray-Ban Meta --Bluetooth--> Galaxy S20 FE (app) --cabo USB, adb reverse--> PC Windows (ponte.py) --Wi-Fi, WebRTC--> Go2
```

| Gesto | Ação | Resultado no robô |
|---|---|---|
| ✌️ Victory | `sentar` | Funcionou |
| ☝️ Pointing_Up | `levantar` | Funcionou |
| 👍 Thumb_Up | `cumprimentar` | Funcionou; o robô confirma em ~4,7 s (só responde quando termina) |
| ✋ Open_Palm | `parar` | Funcionou; confirma em ~0,03 s |

Montagem usada:

| Peça | Detalhe |
|---|---|
| Robô | Go2 comum (não é EDU), firmware 1.1.7, modo `mcf`, sem chave AES |
| Rede | Go2 no Wi-Fi 2.4G de casa; IP mudou de `192.168.1.105` para `192.168.1.106` (DHCP). PC no cabo, `192.168.1.102` |
| PC | Windows 11, Python 3.11 em `mvp-gesto/.venv`, `PYTHONUTF8=1` obrigatório |
| Celular | Galaxy S20 FE (SM-G780G), Android 13, driver USB da Samsung |
| Óculos | Ray-Ban Meta "RB Meta 00P5", Developer Mode ligado |

## 1. Salvar no git

Feito em 12/11/2026, na branch `go2-comum-oculos-no-robo`, com PR para o `main`. O que entrou:

| Arquivo | Mudança |
|---|---|
| `mvp-gesto/ponte.py` | Truques rodam em segundo plano: o laço continua lendo heartbeat e `parar` (antes o vigia mandava `StopMove` no meio do `sentar` e o Go2 levantava sozinho). `PRAZO_TRUQUE_S = 8` (o `Hello` passa de 2 s). Erro sem texto vira o nome do erro (`TimeoutError`). Log do tempo de resposta de cada comando |
| `mvp-gesto/tests/test_ponte.py`, `tests/test_go2_webrtc.py` | 3 testes novos (49 no total, todos passando) |
| `app-android/.../MainActivity.kt` | Registrar só registra se ainda não estiver registrado; diagnóstico dos óculos no log (tag `gestos`); botão "Atualizar óculos"; botões em linha própria (antes saíam da tela) |
| `app-android/app/build.gradle.kts` | `mwdat_application_id` e `mwdat_client_token` vazios, como no app de exemplo da Meta |

## 2. Atualizar a documentação

- [x] Tabela "Estado" do `README.md` e do `mvp-gesto/README.md`: ponte `go2-webrtc` e óculos testados no robô real.
- [x] Contagem de testes (49) no `AGENTS.md`, `mvp-gesto/README.md`, `docs/guia-app-android.md` e `docs/plano.md`.
- [ ] `AGENTS.md`: robô comum sem Jetson, então só o caminho A existe para ele; comandos para Windows.
- [ ] `app-android/README.md`: montagem no Windows (JDK 17, porque o Java 25 do Android Studio não funciona com o Gradle 8.14.1; `local.properties` com barras normais; driver USB da Samsung).
- [ ] `docs/pesquisa.md`: erro `START_ERROR_DAT_APP_ON_THE_GLASSES_UPDATE_REQUIRED` e como foi resolvido (ver seção 7).
- [ ] `docs/arquitetura.md`: no Go2 comum o caminho B (Jetson + DDS) não existe.

## 3. Testes de movimento no robô

Ainda não feitos. Pelo `teclado.py`, com espaço livre e alguém no controle físico (roteiro em `docs/plano.md`):

- [ ] `frente`, `tras`, `girar_esq`, `girar_dir`: anda e para sozinho em 1 s.
- [ ] `segurar frente 3` e `parar` no meio: para na hora.
- [ ] `teste_heartbeat`: para quando o heartbeat some.
- [ ] Matar a ponte com `kill` forçado no meio de um movimento: o Go2 para sozinho? Em quanto tempo? É o teste de segurança mais importante, porque no Go2 comum o vigia fica no PC, não no robô.
- [ ] Repetir derrubando o Wi-Fi do PC.

## 4. Ajustes

- [ ] Prazo dos truques: medir cada um (o log da ponte mostra `robô respondeu X em Y s`) e baixar o `PRAZO_TRUQUE_S` de 8 s para o necessário. Medido até agora: `Hello` ~4,7 s; `Sit` coube em 2 s.
- [ ] `checar_go2.py` avisa que a ponte espera o modo `normal`, mas no firmware 1.1.7 o robô fica em `mcf` e tudo funcionou. Ajustar o aviso.
- [ ] Observar o `heartbeat perdido` (7 vezes no teste com a câmera do celular) e as reconexões em sequência do app.

## 5. Próximas funções

- [ ] **Gestos para andar**: hoje andar só pelo teclado.
- [ ] **Voz**: não existe ainda. Começar pelo microfone do celular (reconhecimento de fala do Android, offline, palavras fixas: "senta", "levanta", "pata", "para"), passando pela mesma lista fechada da ponte. Microfone dos óculos junto com a câmera derruba o vídeo no Android ([issue #159](https://github.com/facebook/meta-wearables-dat-android/issues/159)). Vale testar se os óculos pareados no PC funcionam como microfone.
- [ ] **Sem cabo**: celular falando com a ponte pelo Wi-Fi (`ws://192.168.1.102:8765`). Precisa liberar o Python do `.venv` no firewall do Windows.
- [ ] Teste dos 5 minutos sem disparo falso e 9 de 10 por gesto (critério de pronto do `docs/guia-app-android.md`).
- [ ] G1, depois.

## 6. Rede e robô

- [ ] **Fixar o IP do Go2 no roteador** (reserva de DHCP). Ele já mudou uma vez e a ponte deu `LocalSignalingPortError`.
- **Não atualizar o firmware do Go2.** A partir do 1.1.15 ele passa a exigir chave AES, e há relato de Go2 comum que não conecta no 1.1.15 ([issue #59](https://github.com/legion1581/unitree_webrtc_connect/issues/59)).
- **App da Unitree sempre fechado** antes de ligar a ponte. O robô aceita um cliente por vez (`RobotBusyError`).

## 7. Se a câmera dos óculos parar de novo

Erro no log do celular: `START_ERROR_DAT_APP_ON_THE_GLASSES_UPDATE_REQUIRED` ("Your glasses need an update"), mesmo com os óculos atualizados.

O que resolveu em 05/11/2026: no Meta AI, **desligar o Developer Mode, esperar e ligar de novo**. Isso reinstalou o componente do SDK que roda nos óculos. O firmware não era o problema: o SDK dizia `COMPATIBLE`.

O que não resolveu: reiniciar os óculos, registrar de novo, o botão "Atualizar óculos" (o Meta AI respondeu "indisponível"). Restaurar de fábrica não foi preciso. Referência: [issue #192](https://github.com/facebook/meta-wearables-dat-android/issues/192).

## Como religar tudo

```powershell
# 1. Ponte (app da Unitree fechado; confira o IP do robô)
cd C:\Users\lucas\Desktop\META\mvp-gesto
$env:PYTHONUTF8 = "1"
.venv\Scripts\python.exe ponte.py --robo go2-webrtc --ip 192.168.1.106 2>&1 | Tee-Object -FilePath ponte.log

# 2. Celular no cabo (outro PowerShell)
& "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" reverse tcp:8765 tcp:8765
```

No app: fonte `óculos` → Conectar → gestos. Para desligar: Ctrl+C na ponte (ela manda `StopMove` antes de sair).
