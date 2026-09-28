# Óculos Meta Ray-Ban Gen 2: o que dá para usar

> Conferido em 28/09/2026 nas fontes oficiais listadas no fim. Nada foi testado com os óculos ainda.

## Em resumo

- **Nenhum código roda nos óculos.** O app roda no celular e recebe câmera e áudio dos óculos pelo **Meta Wearables Device Access Toolkit (DAT)**.
- **O assistente Meta AI é fechado.** Então o gesto tem que ser reconhecido no celular, com um modelo de visão sobre o vídeo da câmera.
- **O Gen 2 não tem tela.** O retorno para quem usa é som (alto-falante dos óculos) ou a tela do celular.
- **Publicar o app para qualquer pessoa ainda não é possível.** A distribuição é só para testers.

## Versão do SDK

| O quê | Situação |
|---|---|
| Anúncio | "Wearables Device Access Toolkit 1.0" anunciado em 24/09/2026 no [recap do Meta Connect](https://developers.meta.com/blog/meta-connect-recap-ai-glasses/): abrir apps com "Hey Meta", reconhecimento de fala, streaming de movimento da cabeça e captura de câmera |
| GitHub | O [CHANGELOG do Android](https://github.com/facebook/meta-wearables-dat-android/blob/main/CHANGELOG.md) e o [do iOS](https://github.com/facebook/meta-wearables-dat-ios/blob/main/CHANGELOG.md) ainda param na **0.9.0 (03/08/2026)** |
| Publicação | O [FAQ](https://developers.meta.com/wearables/faq/) diz que a submissão para publicação vem "soon". Em 23/09/2026 ainda não estava aberta ([VR.org](https://vr.org/articles/meta-glasses-three-tiers-wearables-toolkit-publishing-connect-2026)) |

## Dispositivos suportados

Ray-Ban Meta Gen 1 e Gen 2, Ray-Ban Meta Display, Oakley Meta HSTN e Oakley Meta Vanguard. O que cada recurso suporta varia por modelo ([FAQ](https://developers.meta.com/wearables/faq/)).

## Recursos

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

## Android: câmera e microfone juntos derrubam o vídeo

No Android o vídeo e o microfone (HFP/SCO) dividem o mesmo rádio Bluetooth. No iOS, desde a 0.8, o vídeo vai por Wi-Fi e o problema não existe.

| Medição | Resultado | Fonte |
|---|---|---|
| Só vídeo | ~15 a 17 fps | [Issue #159](https://github.com/facebook/meta-wearables-dat-android/issues/159) |
| Vídeo + microfone dos óculos | ~1 a 3 fps | [Issue #159](https://github.com/facebook/meta-wearables-dat-android/issues/159) |
| Vídeo + mic, SDK 0.9.0 | ~0,46 fps (Galaxy A17 5G), ~1,3 fps (Galaxy Z Fold 7) | [Issue #181](https://github.com/facebook/meta-wearables-dat-android/issues/181) |

Na issue #181 a Meta respondeu que transporte por Wi-Fi no Android está "on our bucket list".

**Para este projeto:** o gesto usa só a câmera, então não é afetado. O problema volta quando entrar voz.

## Testar sem os óculos: MockDeviceKit

Vem junto com o SDK e finge um par de óculos pareado dentro do app ([documentação](https://wearables.developer.meta.com/docs/develop/dat/mock-device-kit/)).

- Câmera a partir de um **vídeo gravado (H.265)** ou da câmera do próprio celular.
- Foto a partir de uma imagem.
- Estados: ligado/desligado, no rosto ou não, hastes dobradas ou não.
- Toque e toque longo no touchpad.
- Até **3 óculos falsos** ao mesmo tempo.
- Android: `pairGlasses(GlassesModel.RAYBAN_META)`, `setCameraFeed(...)` ([guia Android](https://wearables.developer.meta.com/docs/testing-mdk-android/)).
- iOS: roda em simulador, inclusive em CI ([guia iOS](https://wearables.developer.meta.com/docs/develop/dat/testing-mdk-ios/)).

## Requisitos para desenvolver

- Conta no Wearables Developer Center e Developer Mode ligado nos óculos (app Meta AI).
- Android: pacotes via GitHub Packages, com token GitHub de escopo `read:packages` ([README do SDK](https://github.com/facebook/meta-wearables-dat-android)).
- iOS: a partir da 0.9.0, iOS 17.2 ou mais novo.
- Só funciona por completo nos países onde os óculos com IA são vendidos.

## Reconhecer o gesto: MediaPipe

[MediaPipe Gesture Recognizer](https://developers.google.com/edge/mediapipe/solutions/vision/gesture_recognizer) roda no Android e reconhece, sem treino:

`Closed_Fist` · `Open_Palm` · `Pointing_Up` · `Thumb_Down` · `Thumb_Up` · `Victory` · `ILoveYou`

- Modos: `IMAGE`, `VIDEO` e `LIVE_STREAM` (câmera ao vivo).
- Gestos novos: dá para treinar um classificador próprio com o Model Maker.

## Fontes

- [Meta Connect Recap: AI glasses (24/09/2026)](https://developers.meta.com/blog/meta-connect-recap-ai-glasses/)
- [Introducing the Meta Wearables Device Access Toolkit](https://developers.meta.com/blog/introducing-meta-wearables-device-access-toolkit/)
- [Wearables FAQ](https://developers.meta.com/wearables/faq/)
- [meta-wearables-dat-android](https://github.com/facebook/meta-wearables-dat-android) · [meta-wearables-dat-ios](https://github.com/facebook/meta-wearables-dat-ios)
- [Microfones e alto-falantes](https://wearables.developer.meta.com/docs/develop/dat/microphones-and-speakers/)
- [Mock Device Kit](https://wearables.developer.meta.com/docs/develop/dat/mock-device-kit/)
- [Extentos: especificações do DAT (terceiros)](https://extentos.com/docs/vendors/meta)
- [MediaPipe Gesture Recognizer](https://developers.google.com/edge/mediapipe/solutions/vision/gesture_recognizer)
