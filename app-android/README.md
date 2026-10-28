# App Android: gesto -> ponte

O `gesto_webcam.py` em Kotlin: câmera do celular -> MediaPipe -> filtro anti-disparo -> WebSocket para a [ponte](../mvp-gesto/ponte.py). Especificação e critério de pronto no [guia](../docs/guia-app-android.md).

## Rodar

Precisa de Android Studio (ou só do Android SDK), JDK 17 e um celular com Android 12 ou mais novo, com Depuração USB ligada.

```
# terminal 1: a ponte, sem robô
cd mvp-gesto && source .venv/bin/activate
python ponte.py --robo mock

# terminal 2: o app no celular pelo cabo
cd app-android
adb reverse tcp:8765 tcp:8765        # ws://localhost:8765 do celular -> ponte no laptop
./gradlew installDebug
adb shell am start -n com.metaunitree.gestos/.MainActivity
```

Ou abra a pasta `app-android/` no Android Studio e aperte Run. O modelo `gesture_recognizer.task` é baixado sozinho no primeiro build, para `app/src/main/assets/` (fora do git).

Pelo Wi-Fi, sem cabo: no campo "ponte" do app, `ws://<ip-do-laptop>:8765` (no Mac: `ipconfig getifaddr en0`) e Conectar.

Testes do filtro (os mesmos casos de `mvp-gesto/tests/test_filtro.py`):

```
./gradlew testDebugUnitTest
```

## Medir: o que o MediaPipe viu

Cada vez que o app abre, ele grava um CSV com uma linha por quadro (`t_ms,gesto,confianca,tem_mao,acao`, as mesmas colunas do `--log` do `gesto_webcam.py`). O arquivo é fechado quando o app sai da tela. Para puxar:

```
adb shell input keyevent KEYCODE_HOME     # fecha o arquivo
adb pull /sdcard/Android/data/com.metaunitree.gestos/files/ csv/
```

## Arquivos

| Arquivo | O que faz | No Python |
|---|---|---|
| `FonteDeFrames.kt` | Interface da fonte de frames e `CameraCelular` (CameraX, 640x480, imagem já girada) | `cv2.VideoCapture` |
| `ReconhecedorGesto.kt` | MediaPipe Gesture Recognizer em `LIVE_STREAM` | `recognize_for_video` |
| `FiltroGesto.kt` | Filtro anti-disparo e os mapas gesto -> ação | `filtro.py`, `MAPA` |
| `ClientePonte.kt` | WebSocket (OkHttp): ações, heartbeat, acks | `websockets` em `gesto_webcam.py` |
| `RegistroCsv.kt` | CSV com o gesto e a confiança de cada quadro | `--log` |
| `MainActivity.kt` | Liga tudo e desenha a tela (Compose) | `main()` e `desenhar()` |

Para os óculos: uma `CameraOculos : FonteDeFrames` com o SDK Meta DAT, no lugar da `CameraCelular`.

## Segurança

- O heartbeat (a cada 100 ms) sai do callback do MediaPipe, um por frame processado. Se a câmera ou o reconhecimento travar, o heartbeat para e a ponte para o robô em 300 ms.
- `onStop` fecha a conexão: app em segundo plano -> a ponte para o robô.
- Botão PARAR manda `parar` sem depender de gesto.

## Estado

Testado em 28/10/2026 num Galaxy S25+ (Android 17), pelo cabo com `adb reverse`, com a ponte em `mock`:

- Build e 12 testes do filtro passando.
- Conecta na ponte e processa ~15 fps.
- App para segundo plano -> ponte mostra `cliente desconectado -> parar`; ao voltar, reconecta.

Falta conferir os itens do [critério de pronto](../docs/guia-app-android.md#pronto-quando): gestos ao vivo, 9 de 10 por gesto, teste dos 5 minutos, pelo Wi-Fi.
