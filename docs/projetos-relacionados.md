# Projetos relacionados

> Todos os links foram abertos e conferidos em 28/09/2026. Não achei nenhum projeto público que faça o caminho completo óculos Meta -> robô Unitree; as peças existem separadas.

## O mais próximo do objetivo final

### [spectacles-dimensional-os](https://github.com/V4C38/spectacles-dimensional-os) (MIT)

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

## Gesto de mão -> robô

| Projeto | Robô | O que faz |
|---|---|---|
| [lez666/Unitree-Go2-GestureDetection](https://github.com/lez666/Unitree-Go2-GestureDetection) | Go2 | MediaPipe na câmera frontal do robô + `unitree_sdk2_python`. Virar o pulso = levantar/sentar, "V" = Hello, dois dedos = Heart. Roda no laptop ou direto no Jetson |
| [avazahedi/go1-gesture-command](https://github.com/avazahedi/go1-gesture-command) | Go1 | ROS 2, MediaPipe + classificador TensorFlow com 8 gestos -> comandos de movimento |

## Apps com o SDK dos óculos Meta

| Projeto | Plataforma | O que faz |
|---|---|---|
| [Intent-Lab/VisionClaw](https://github.com/Intent-Lab/VisionClaw) | iOS 17+, Android 14+ | Assistente com Gemini Live: áudio 16 kHz e ~1 frame/s da câmera dos óculos |
| [FedeSack/rayban-meta-dat-android](https://github.com/FedeSack/rayban-meta-dat-android) | Android | Stream da câmera dos óculos com HUD de latência (código no branch `develop`) |
| [straff2002/OpenGlasses](https://github.com/straff2002/OpenGlasses) | iOS | Assistente de voz com vários LLMs, inclusive locais (licença BSL 1.1) |
| [amanshah0729/vision](https://github.com/amanshah0729/vision) | iOS | Câmera do Ray-Ban Display repassada a apps web por um servidor ponte |

## Unitree por voz ou LLM

| Projeto | Robô | O que faz |
|---|---|---|
| [lpigeon/unitree-go2-mcp-server](https://github.com/lpigeon/unitree-go2-mcp-server) | Go2 | Linguagem natural -> LLM -> MCP -> ROS 2 |
| [SCMU-AILAB/Go2Agent](https://github.com/SCMU-AILAB/Go2Agent) | Go2 | Voz local: Faster Whisper + Ollama + Piper |
| [Yao0454/G1Agent](https://github.com/Yao0454/G1Agent) | G1 | Voz com Whisper + Ollama, câmera D435i |
| [SaxionMechatronics/unitree_converse](https://github.com/SaxionMechatronics/unitree_converse) | G1 | Conversa por voz toda no Jetson Orin NX do robô (Llama 3.2 3B) |
| [ArtZap/KuzmichAI-UnitreeG1](https://github.com/ArtZap/KuzmichAI-UnitreeG1) | G1 | Assistente de voz offline e multilíngue |
| [jhaiq/GO2-seeing-eye-dog](https://github.com/jhaiq/GO2-seeing-eye-dog) | Go2 | Chamar o robô por voz: Whisper, YOLOv8, Nav2, Jetson Orin |
| [Go2 EDU com voz em tempo real (HackMD)](https://hackmd.io/@c12hQ00ySVi6JYIERU7bCg/ByAOr12qJg) | Go2 | Guia: microfone do robô -> Whisper -> ChatGPT -> alto-falante |

## Teleoperação por headset XR

| Projeto | O que faz |
|---|---|
| [unitreerobotics/xr_teleoperate](https://github.com/unitreerobotics/xr_teleoperate) | Oficial. Vision Pro, PICO 4 Ultra Enterprise e Quest 3 controlam braços e mãos de G1, H1, H2 e R1 pelo navegador (WebRTC + WebSocket). Roda também contra o `unitree_sim_isaaclab` |
| [AShtanev/robotics-demos](https://github.com/AShtanev/robotics-demos) | Vídeos de teleoperação VR, voz e navegação em G1, H1, H2 e Go2 |

## Pesquisa

- [EgoMimic](https://ai.meta.com/blog/egomimic-project-aria-georgia-tech-ego4d-robotics-embodied-ai/) (Georgia Tech + Meta): vídeo em primeira pessoa dos óculos Project Aria usado para treinar robôs. É o uso mais comum de óculos em robótica hoje: ensinar, não comandar em tempo real.
