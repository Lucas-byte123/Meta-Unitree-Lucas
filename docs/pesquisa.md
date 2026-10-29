# Pesquisa

> O que foi levantado sobre os óculos, os robôs e projetos parecidos. Cada seção diz quando foi conferida. Como o projeto usa isso está na [arquitetura](arquitetura.md); o que fazer, no [plano](plano.md).

- [Óculos Ray-Ban Meta Gen 2](#óculos-ray-ban-meta-gen-2)
- [Robôs Unitree Go2 e G1 EDU](#robôs-unitree-go2-e-g1-edu)
- [Projetos relacionados](#projetos-relacionados)

## Óculos Ray-Ban Meta Gen 2

> Conferido em 28/09/2026 nas fontes oficiais listadas no fim; versão do SDK e requisitos atualizados em 28/10/2026. Nada foi testado com os óculos ainda.

### Em resumo

- **Nenhum código roda nos óculos.** O app roda no celular e recebe câmera e áudio dos óculos pelo **Meta Wearables Device Access Toolkit (DAT)**.
- **O assistente Meta AI é fechado.** Então o gesto tem que ser reconhecido no celular, com um modelo de visão sobre o vídeo da câmera.
- **O Gen 2 não tem tela.** O retorno para quem usa é som (alto-falante dos óculos) ou a tela do celular.
- **Publicar o app para qualquer pessoa ainda não é possível.** A distribuição é só para testers.

### Versão do SDK

| O quê | Situação |
|---|---|
| Anúncio | "Wearables Device Access Toolkit 1.0" anunciado em 24/09/2026 no [recap do Meta Connect](https://developers.meta.com/blog/meta-connect-recap-ai-glasses/): abrir apps com "Hey Meta", reconhecimento de fala, streaming de movimento da cabeça e captura de câmera |
| Android | **1.0.0 em 24/09/2026 e 1.0.1 em 09/10/2026** ([CHANGELOG](https://github.com/facebook/meta-wearables-dat-android/blob/main/CHANGELOG.md)). A 1.0.1 corrige congelamentos de quadro e travadas no `Stream`. Inputs, Motion, Speech, captura de foto e áudio no stream entram como experimentais: dá para testar, mas não para publicar |
| Publicação | O [FAQ](https://developers.meta.com/wearables/faq/) diz que a submissão para publicação vem "soon". Em 23/09/2026 ainda não estava aberta ([VR.org](https://vr.org/articles/meta-glasses-three-tiers-wearables-toolkit-publishing-connect-2026)) |

### Dispositivos suportados

Ray-Ban Meta Gen 1 e Gen 2, Ray-Ban Meta Display, Oakley Meta HSTN e Oakley Meta Vanguard. O que cada recurso suporta varia por modelo ([FAQ](https://developers.meta.com/wearables/faq/)).

### Recursos

| Recurso | Situação | Fonte |
|---|---|---|
| Vídeo ao vivo da câmera | Sim. 360x640, 504x896 ou 720x1280, a 2/7/15/24/30 fps | [Extentos](https://extentos.com/docs/vendors/meta) (terceiros) |
| Foto | Sim. JPEG, sensor de 12 MP | [Extentos](https://extentos.com/docs/vendors/meta) |
| Microfone | Sim, por Bluetooth HFP, 16 kHz mono, com beamforming na voz de quem usa | [Meta: microfones e alto-falantes](https://wearables.developer.meta.com/docs/develop/dat/microphones-and-speakers/) |
| Áudio junto com o vídeo | **Beta.** Microfone vem dentro do stream da câmera, sem HFP. Só nos canais de desenvolvimento e beta | [Meta: microfones e alto-falantes](https://wearables.developer.meta.com/docs/develop/dat/microphones-and-speakers/) |
| Alto-falante | Sim. A2DP para áudio bom; HFP para voz, e os dois concorrem | [Extentos](https://extentos.com/docs/vendors/meta) |
| Movimento da cabeça (IMU) | Anunciado na 1.0 ("motion streaming"). Não existia na 0.8.0 | [Recap Connect](https://developers.meta.com/blog/meta-connect-recap-ai-glasses/), [Extentos](https://extentos.com/docs/vendors/meta) |
| "Hey Meta" | Só para abrir o app (1.0). O Meta AI em si continua fechado | [Recap Connect](https://developers.meta.com/blog/meta-connect-recap-ai-glasses/) |
| Tela | Não no Gen 2. Só o Ray-Ban Display | [FAQ](https://developers.meta.com/wearables/faq/) |

### Android: câmera e microfone juntos derrubam o vídeo

No Android o vídeo e o microfone (HFP/SCO) dividem o mesmo rádio Bluetooth. No iOS, desde a 0.8, o vídeo vai por Wi-Fi e o problema não existe.

| Medição | Resultado | Fonte |
|---|---|---|
| Só vídeo | ~15 a 17 fps | [Issue #159](https://github.com/facebook/meta-wearables-dat-android/issues/159) |
| Vídeo + microfone dos óculos | ~1 a 3 fps | [Issue #159](https://github.com/facebook/meta-wearables-dat-android/issues/159) |
| Vídeo + mic, SDK 0.9.0 | ~0,46 fps (Galaxy A17 5G), ~1,3 fps (Galaxy Z Fold 7) | [Issue #181](https://github.com/facebook/meta-wearables-dat-android/issues/181) |

Na issue #181 a Meta respondeu que transporte por Wi-Fi no Android está "on our bucket list".

**Para este projeto:** o gesto usa só a câmera, então não é afetado. O problema volta quando entrar voz.

### Testar sem os óculos: MockDeviceKit

Vem junto com o SDK e finge um par de óculos pareado dentro do app ([documentação](https://wearables.developer.meta.com/docs/develop/dat/mock-device-kit/)).

- Câmera a partir de um **vídeo gravado (H.265)** ou da câmera do próprio celular.
- Foto a partir de uma imagem.
- Estados: ligado/desligado, no rosto ou não, hastes dobradas ou não.
- Toque e toque longo no touchpad.
- Até **3 óculos falsos** ao mesmo tempo.
- Android: `pairGlasses(GlassesModel.RAYBAN_META)`, `setCameraFeed(...)` ([guia Android](https://wearables.developer.meta.com/docs/testing-mdk-android/)).
- iOS: roda em simulador, inclusive em CI ([guia iOS](https://wearables.developer.meta.com/docs/develop/dat/testing-mdk-ios/)).

### Requisitos para desenvolver

- Conta no Wearables Developer Center e Developer Mode ligado nos óculos (app Meta AI).
- Android: pacotes no **Maven Central** (`com.meta.wearable:mwdat-core`, `mwdat-camera`, `mwdat-mockdevice`...), **sem token**; até a 0.9 era pelo GitHub Packages com token `read:packages` ([README do SDK](https://github.com/facebook/meta-wearables-dat-android)).
- Android: o app de exemplo `CameraAccess` usa `minSdk 31` (Android 12), `compileSdk 36`, JDK 17, Kotlin 2.2 e Jetpack Compose ([build.gradle.kts](https://github.com/facebook/meta-wearables-dat-android/blob/main/samples/CameraAccess/app/build.gradle.kts)).
- Com Developer Mode ligado, o app roda sem o `APPLICATION_ID` e o `CLIENT_TOKEN` do Wearables Developer Center; sem Developer Mode, os dois vão no manifest ([manifest do exemplo](https://github.com/facebook/meta-wearables-dat-android/blob/main/samples/CameraAccess/app/src/main/AndroidManifest.xml)).
- iOS: a partir da 0.9.0, iOS 17.2 ou mais novo.
- Só funciona por completo nos países onde os óculos com IA são vendidos.

**Para assistentes de código:** o repositório do SDK traz skills para Claude Code, Codex e Cursor (`install-skills.sh`) e um servidor MCP público com a documentação do DAT, `https://mcp.developer.meta.com/wearables`, sem autenticação ([README do SDK](https://github.com/facebook/meta-wearables-dat-android#readme)).

### Reconhecer o gesto: MediaPipe

[MediaPipe Gesture Recognizer](https://developers.google.com/edge/mediapipe/solutions/vision/gesture_recognizer) roda no Android e reconhece, sem treino:

`Closed_Fist` · `Open_Palm` · `Pointing_Up` · `Thumb_Down` · `Thumb_Up` · `Victory` · `ILoveYou`

- Modos: `IMAGE`, `VIDEO` e `LIVE_STREAM` (câmera ao vivo).
- Gestos novos: dá para treinar um classificador próprio com o Model Maker.

### Fontes

- [Meta Connect Recap: AI glasses (24/09/2026)](https://developers.meta.com/blog/meta-connect-recap-ai-glasses/)
- [Introducing the Meta Wearables Device Access Toolkit](https://developers.meta.com/blog/introducing-meta-wearables-device-access-toolkit/)
- [Wearables FAQ](https://developers.meta.com/wearables/faq/)
- [meta-wearables-dat-android](https://github.com/facebook/meta-wearables-dat-android) · [meta-wearables-dat-ios](https://github.com/facebook/meta-wearables-dat-ios)
- [Microfones e alto-falantes](https://wearables.developer.meta.com/docs/develop/dat/microphones-and-speakers/)
- [Mock Device Kit](https://wearables.developer.meta.com/docs/develop/dat/mock-device-kit/)
- [Extentos: especificações do DAT (terceiros)](https://extentos.com/docs/vendors/meta)
- [MediaPipe Gesture Recognizer](https://developers.google.com/edge/mediapipe/solutions/vision/gesture_recognizer)

## Robôs Unitree Go2 e G1 EDU

> Conferido em 28/09/2026 nos repositórios oficiais da Unitree. Nada foi testado nos robôs ainda.

### Em resumo

- Os dois robôs aceitam **comandos prontos de alto nível** (andar, parar, sentar, dar a pata, acenar...) pelo SDK oficial, que fala DDS na rede interna do robô.
- Por isso a ponte roda no **computador de bordo (Jetson)** do modelo EDU e recebe os comandos do celular por Wi-Fi.
- **No simulador esses comandos não existem.** Lá o robô só anda com uma **política de locomoção** rodando por cima.

### Formas de mandar comandos

| Caminho | Oficial | Robôs | Observações |
|---|---|---|---|
| [unitree_sdk2_python](https://github.com/unitreerobotics/unitree_sdk2_python) | Sim | Go2, G1 | Python >= 3.8 e `cyclonedds == 0.10.2`. **É o que a ponte usa** |
| [unitree_ros2](https://github.com/unitreerobotics/unitree_ros2) | Sim | Go2, B2, H1 | ROS 2 Foxy (Ubuntu 20.04) ou Humble (22.04). Comandos em `/api/sport/request`; estado em `/sportmodestate`, `/lowstate`, `/wirelesscontroller` |
| [unitree_webrtc_connect](https://github.com/legion1581/unitree_webrtc_connect) | Não (MIT) | Go2 AIR/PRO/EDU, G1 AIR/EDU | Mesmo protocolo do app da Unitree. Desde o firmware G1 1.5.1 / Go2 1.1.15 exige uma chave AES por robô |
| [go2_ros2_sdk](https://github.com/abizovnuralem/go2_ros2_sdk) | Não | Go2 AIR/PRO/EDU | ROS 2 por WebRTC (Wi-Fi) ou CycloneDDS (cabo), com LiDAR, câmera, SLAM e Nav2 |

**Firmware do Go2:** o firmware 1.1.6 mudou os IDs das APIs de sport, e SDK Python antigo dá `3203 unknown api`. O [PR #76](https://github.com/unitreerobotics/unitree_sdk2_python/pull/76) alinha o SDK Python com essa versão.

### Go2: `SportClient`

Arquivo: [`unitree_sdk2py/go2/sport/sport_client.py`](https://github.com/unitreerobotics/unitree_sdk2_python/blob/master/unitree_sdk2py/go2/sport/sport_client.py)

| Tipo | Métodos |
|---|---|
| Postura | `Damp` `BalanceStand` `StandUp` `StandDown` `RecoveryStand` `Sit` `RiseSit` `Euler` `Pose` |
| Andar | `Move(vx, vy, vyaw)` `StopMove` `SpeedLevel` `FreeWalk` `ClassicWalk` `StaticWalk` `TrotRun` `CrossStep` `WalkUpright` `FreeBound` `FreeJump` `FreeAvoid` |
| Truques | `Hello` (dar a pata) `Stretch` `Content` `Dance1` `Dance2` `Heart` `Scrape` `FrontJump` `FrontPounce` `FrontFlip` `LeftFlip` `BackFlip` `HandStand` |
| Outros | `AutoRecoverySet` `AutoRecoveryGet` `SwitchAvoidMode` `SwitchJoystick` |

Exemplo oficial: `example/go2/high_level/go2_sport_client.py <interface-de-rede>`.

### G1: `LocoClient` e `G1ArmActionClient`

[`LocoClient`](https://github.com/unitreerobotics/unitree_sdk2_python/blob/master/unitree_sdk2py/g1/loco/g1_loco_client.py):

| Tipo | Métodos |
|---|---|
| Estado | `Damp` `ZeroTorque` `Start` `Squat2StandUp` `Lie2StandUp` `StandUp2Squat` `Sit` `HighStand` `LowStand` `BalanceStand` `SetStandHeight` `SetBalanceMode` `GetFsmId` `SetFsmId` |
| Andar | `Move(vx, vy, vyaw)` `SetVelocity` `StopMove` `SetSpeedMode` |
| Gestos | `WaveHand` (acenar) `ShakeHand` (aperto de mão) |
| Controle | `SetTaskId` `SwitchToUserCtrl` `SwitchToInternalCtrl` |

[`G1ArmActionClient`](https://github.com/unitreerobotics/unitree_sdk2_python/blob/master/unitree_sdk2py/g1/arm/g1_arm_action_client.py), `ExecuteAction(id)`:

| Ação | ID | Ação | ID |
|---|---|---|---|
| two-hand kiss | 11 | reject | 22 |
| left kiss | 12 | right hand up | 23 |
| right kiss | 13 | x-ray | 24 |
| hands up | 15 | face wave | 25 |
| clap | 17 | high wave | 26 |
| high five | 18 | shake hand | 27 |
| hug | 19 | release arm | 99 |
| heart | 20 | right heart | 21 |

**Atenção no G1:** a parada por software é `StopMove`. `Damp` tira o torque dos motores e o humanoide cai, então só com ele pendurado no pórtico.

### Simulação

> Decisão de 08/10/2026: os testes vão direto no robô real, sem simulação. Esta seção fica como referência do porquê.

#### O problema

O [unitree_mujoco](https://github.com/unitreerobotics/unitree_mujoco) usa o mesmo DDS do robô real, mas a própria página diz: *"Current version only supports low-level development"*. Ou seja, só comando motor a motor. `Move`, `Sit`, `Hello`, `WaveHand` e as ações de braço não funcionam lá.

O que ele tem:
- Robôs: Go2, Go2w, B2, B2w, H1, G1, H2, AS2.
- Simula o controle sem fio da Unitree com um gamepad (Xbox ou Switch).
- Recomenda um DDS domain id diferente do robô real (o real usa 0; os exemplos do simulador usam 1).

#### A solução: política de locomoção

Uma rede treinada que recebe o estado do robô e um comando de velocidade e devolve a posição de cada motor. Repositórios oficiais para treinar e rodar:

| Repositório | Simulador | Robôs | Política pronta no repositório |
|---|---|---|---|
| [unitree_rl_gym](https://github.com/unitreerobotics/unitree_rl_gym) | Isaac Gym, com `deploy_mujoco` | Go2, H1, H1_2, G1 | **G1:** `deploy/pre_train/g1/motion.pt`. Go2 não tem config de MuJoCo |
| [unitree_rl_lab](https://github.com/unitreerobotics/unitree_rl_lab) | Isaac Lab 2.3.0 / Isaac Sim 5.1.0, sim2sim em MuJoCo | Go2, H1, G1-29dof | Não encontrada |
| [unitree_rl_mjlab](https://github.com/unitreerobotics/unitree_rl_mjlab) | MuJoCo | Velocidade: Go2, G1, G1-23dof, H1_2, A2, R1. Imitação de movimento: G1 | Não; exporta `policy.onnx` depois de treinar |

**Conclusão para o projeto:** para o **Go2 não existe política pronta publicada**, então a simulação do Go2 depende de uma política própria já treinada. Para o **G1** existe a do `unitree_rl_gym`.

#### Isaac Sim

| Repositório | O que é |
|---|---|
| [unitree_sim_isaaclab](https://github.com/unitreerobotics/unitree_sim_isaaclab) | Oficial. G1 (29 DoF) e H1-2 (27 DoF), sem Go2. Tarefas `Wholebody` andam. Mesmos tópicos DDS do robô real. Testado em RTX 3080/3090/4090 (série 50 com Isaac Sim 5.0.0); Ubuntu 20.04 ou 22.04 |
| [go2_omniverse](https://github.com/abizovnuralem/go2_omniverse) | Comunidade (~1,1 mil estrelas). Go2 e G1 no Isaac Lab com ROS 2 `cmd_vel`, câmera, LiDAR e Nav2 |

Para gesto -> andar/parar, o MuJoCo basta. Isaac passa a valer quando entrar câmera do robô, navegação ou braços do G1.

### Fontes

- [unitree_sdk2_python](https://github.com/unitreerobotics/unitree_sdk2_python)
- [unitree_ros2](https://github.com/unitreerobotics/unitree_ros2)
- [unitree_mujoco](https://github.com/unitreerobotics/unitree_mujoco)
- [unitree_rl_gym](https://github.com/unitreerobotics/unitree_rl_gym) · [unitree_rl_lab](https://github.com/unitreerobotics/unitree_rl_lab) · [unitree_rl_mjlab](https://github.com/unitreerobotics/unitree_rl_mjlab)
- [unitree_sim_isaaclab](https://github.com/unitreerobotics/unitree_sim_isaaclab)
- [unitree_webrtc_connect](https://github.com/legion1581/unitree_webrtc_connect) · [go2_ros2_sdk](https://github.com/abizovnuralem/go2_ros2_sdk) · [go2_omniverse](https://github.com/abizovnuralem/go2_omniverse)

## Projetos relacionados

> Todos os links foram abertos e conferidos em 28/09/2026. Não achei nenhum projeto público que faça o caminho completo óculos Meta -> robô Unitree; as peças existem separadas.

### O mais próximo do objetivo final

#### [spectacles-dimensional-os](https://github.com/V4C38/spectacles-dimensional-os) (MIT)

Óculos AR controlando o Go2: arrasta-se um marcador no espaço e o robô anda até lá.

![Spectacles AR controlando um Unitree Go2](https://media.githubusercontent.com/media/V4C38/spectacles-dimensional-os/main/assets/specs_dimos_hero.gif)

<sub>GIF do repositório [spectacles-dimensional-os](https://github.com/V4C38/spectacles-dimensional-os), © 2026 spectacles-dimensional-os contributors, licença MIT.</sub>

| | |
|---|---|
| Óculos | Snap Spectacles 2024 (kit de desenvolvedor), app em TypeScript no Lens Studio |
| Cérebro | [Dimensional OS](https://github.com/dimensionalOS/dimos) num Mac: mapa, navegação, agente |
| Ponte | AR-Bridge (pacote Python `dimos-ar`), fala com os óculos por WebSocket |
| Alinhamento | AprilTag de 70 mm no robô (1 no Go2, 2 no G1) |
| Destino | Marcador de navegação que o usuário arrasta |
| Parada | Palma esquerda para cima abre o menu no pulso, que tem a parada de emergência |
| Voz | Comandos para um agente GPT-4o no Mac |
| Rede | Mac, óculos e robô no mesmo Wi-Fi, com internet |
| Robôs | Go2 "fully supported & tested"; G1 "supported, not tested" |

Diferença para este projeto: o Ray-Ban Meta Gen 2 não tem tela nem rastreamento de mão nativo, então o marcador AR não se reproduz nele. Os Spectacles ficam anotados como opção de óculos.

##### Como a comunicação acontece

Conferido no README em 08/10/2026. **Os óculos não falam direto com o robô**; tudo passa pelo Mac.

```
Spectacles ──Wi-Fi, WebSocket (porta 8787)──▶ Mac (DimOS + AR-Bridge) ──WebRTC ou DDS──▶ Go2
```

- **Óculos -> Mac:** os Spectacles têm Wi-Fi e rodam o próprio app. Conectam por WebSocket no AR-Bridge; o IP do Mac é digitado nos óculos no primeiro uso. Vão destinos, gestos e imagens da câmera (para achar a AprilTag); voltam posição do robô, rota e LiDAR.
- **Mac -> robô:** o README diz que o Mac mantém a conexão com o Go2 por WebRTC ou DDS. O DimOS acha o robô pelo IP (`export ROBOT_IP=...`).
- **Dedução, não confirmada:** o DimOS lista o Go2 Pro/Air como suportados, e eles não têm Jetson nem acesso por DDS. Então, no Go2 comum, ele provavelmente usa WebRTC pelo Wi-Fi do próprio robô, o mesmo protocolo do app da Unitree (ver [`unitree_webrtc_connect`](#formas-de-mandar-comandos)).

| | spectacles-dimensional-os | Este projeto |
|---|---|---|
| Óculos | Spectacles: têm Wi-Fi e rodam o app | Ray-Ban Meta: sem app próprio, só mandam vídeo ao celular por Bluetooth |
| Quem processa | Mac, fora do robô | Celular (visão) + Jetson, dentro do robô (segurança) |
| Ligação até o robô | Mac -> Go2 pelo Wi-Fi (provavelmente WebRTC) | Jetson -> Go2 pelo cabo interno, DDS do SDK oficial |
| Ponte | AR-Bridge, WebSocket, porta 8787 | `ponte.py`, WebSocket, porta 8765 |

A forma é a mesma: um cliente leve manda comandos por WebSocket para uma ponte, e a ponte comanda o robô. Muda onde a ponte fica.

**O que isso virou no plano:** o caminho deles, com um laptop no lugar do Mac falando com o Go2 por WebRTC, é o **caminho A**, para começar a mover o robô logo; um amigo já teleoperou um Go2 EDU assim. Os riscos continuam: o protocolo não é oficial (engenharia reversa), exige uma chave AES por robô desde o firmware 1.1.15 e a ponte fica fora do robô. Por isso o destino final é o **caminho B**, com Jetson, adaptador Wi-Fi USB e SDK oficial ([arquitetura](arquitetura.md#dois-caminhos-até-o-robô)).

### Gesto de mão -> robô

| Projeto | Robô | O que faz |
|---|---|---|
| [lez666/Unitree-Go2-GestureDetection](https://github.com/lez666/Unitree-Go2-GestureDetection) | Go2 | MediaPipe na câmera frontal do robô + `unitree_sdk2_python`. Virar o pulso = levantar/sentar, "V" = Hello, dois dedos = Heart. Roda no laptop ou direto no Jetson |
| [avazahedi/go1-gesture-command](https://github.com/avazahedi/go1-gesture-command) | Go1 | ROS 2, MediaPipe + classificador TensorFlow com 8 gestos -> comandos de movimento |

### Apps com o SDK dos óculos Meta

| Projeto | Plataforma | O que faz |
|---|---|---|
| [Intent-Lab/VisionClaw](https://github.com/Intent-Lab/VisionClaw) | iOS 17+, Android 14+ | Assistente com Gemini Live: áudio 16 kHz e ~1 frame/s da câmera dos óculos |
| [FedeSack/rayban-meta-dat-android](https://github.com/FedeSack/rayban-meta-dat-android) | Android | Stream da câmera dos óculos com HUD de latência (código no branch `develop`) |
| [straff2002/OpenGlasses](https://github.com/straff2002/OpenGlasses) | iOS | Assistente de voz com vários LLMs, inclusive locais (licença BSL 1.1) |
| [amanshah0729/vision](https://github.com/amanshah0729/vision) | iOS | Câmera do Ray-Ban Display repassada a apps web por um servidor ponte |

### Unitree por voz ou LLM

| Projeto | Robô | O que faz |
|---|---|---|
| [lpigeon/unitree-go2-mcp-server](https://github.com/lpigeon/unitree-go2-mcp-server) | Go2 | Linguagem natural -> LLM -> MCP -> ROS 2 |
| [SCMU-AILAB/Go2Agent](https://github.com/SCMU-AILAB/Go2Agent) | Go2 | Voz local: Faster Whisper + Ollama + Piper |
| [Yao0454/G1Agent](https://github.com/Yao0454/G1Agent) | G1 | Voz com Whisper + Ollama, câmera D435i |
| [SaxionMechatronics/unitree_converse](https://github.com/SaxionMechatronics/unitree_converse) | G1 | Conversa por voz toda no Jetson Orin NX do robô (Llama 3.2 3B) |
| [ArtZap/KuzmichAI-UnitreeG1](https://github.com/ArtZap/KuzmichAI-UnitreeG1) | G1 | Assistente de voz offline e multilíngue |
| [jhaiq/GO2-seeing-eye-dog](https://github.com/jhaiq/GO2-seeing-eye-dog) | Go2 | Chamar o robô por voz: Whisper, YOLOv8, Nav2, Jetson Orin |
| [Go2 EDU com voz em tempo real (HackMD)](https://hackmd.io/@c12hQ00ySVi6JYIERU7bCg/ByAOr12qJg) | Go2 | Guia: microfone do robô -> Whisper -> ChatGPT -> alto-falante |

### Teleoperação por headset XR

| Projeto | O que faz |
|---|---|
| [unitreerobotics/xr_teleoperate](https://github.com/unitreerobotics/xr_teleoperate) | Oficial. Vision Pro, PICO 4 Ultra Enterprise e Quest 3 controlam braços e mãos de G1, H1, H2 e R1 pelo navegador (WebRTC + WebSocket). Roda também contra o `unitree_sim_isaaclab` |
| [AShtanev/robotics-demos](https://github.com/AShtanev/robotics-demos) | Vídeos de teleoperação VR, voz e navegação em G1, H1, H2 e Go2 |

### Pesquisa acadêmica

- [EgoMimic](https://ai.meta.com/blog/egomimic-project-aria-georgia-tech-ego4d-robotics-embodied-ai/) (Georgia Tech + Meta): vídeo em primeira pessoa dos óculos Project Aria usado para treinar robôs. É o uso mais comum de óculos em robótica hoje: ensinar, não comandar em tempo real.
