# MVP: um gesto, uma ação

O caso mais simples da [arquitetura](../docs/arquitetura.md): o celular reconhece o gesto e o robô executa uma ação pronta.

## Fluxo

```
Óculos Ray-Ban Meta Gen 2      câmera -> Bluetooth
        |
Celular Android: app com Meta DAT, só a câmera ligada
   frame -> MediaPipe Gesture Recognizer -> "Thumb_Up" estável por ~0,5 s
        |  WebSocket no Wi-Fi: {"tipo":"acao","acao":"cumprimentar","id":"a1b2"}
Jetson do robô: ponte.py
   valida (lista fechada, cooldown 3 s) -> SDK Unitree (DDS)
        |
Go2: SportClient.Hello()   ou   G1: LocoClient.WaveHand()
```

A ponte responde com um `ack`, e o app pode tocar um som no alto-falante dos óculos para confirmar que o comando chegou.

## Gesto -> ação

Os gestos são os 7 que o MediaPipe reconhece sem treino.

| Gesto | Go2 | G1 |
|---|---|---|
| Thumb_Up | `cumprimentar` -> `Hello()` (dá a pata) | `cumprimentar` -> `WaveHand()` (acena) |
| Victory | `sentar` -> `Sit()` | `high_five` -> braço "high five" |
| Pointing_Up | `levantar` -> `RiseSit()` | |
| ILoveYou | | `palmas` -> braço "clap" |
| Open_Palm | `parar` -> `StopMove()` | `parar` -> `StopMove()` |

Contra disparo acidental: confiança >= 0,7, gesto estável por 8 frames (~0,5 s), só dispara de novo depois de baixar a mão, e a ponte ignora ações por 3 s depois de cada uma ("parar" nunca espera).

## Arquivos

| Arquivo | Onde roda | O que faz |
|---|---|---|
| `ponte.py` | Jetson do robô | Servidor WebSocket; valida e chama o SDK (Go2, G1 ou mock). Para o robô se o cliente cair ou o heartbeat parar. |
| `teclado.py` | Laptop | Manda ações digitadas. |
| `gesto_webcam.py` | Laptop | MediaPipe na webcam -> ponte. Referência para o app Android. |

```
pip install -r requirements.txt
```

O `unitree_sdk2_python` só é necessário no Jetson ([instalação](https://github.com/unitreerobotics/unitree_sdk2_python)).

## Etapas

Cada uma dá para testar sozinha.

**1. Robô obedece a um script.** SSH no Jetson, instalar `unitree_sdk2_python`, rodar `example/go2/high_level/go2_sport_client.py <iface>`. Pronto quando o Go2 der a pata a partir do terminal.

**2. Ponte + teclado.** No Jetson: `python3 ponte.py --robo go2 --iface <iface>`. No laptop, no mesmo Wi-Fi: `python3 teclado.py ws://<ip-do-jetson>:8765` e digitar `cumprimentar`. Sem robô: `--robo mock`.

**3. Gesto na webcam -> robô.**

```
wget https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task
python3 gesto_webcam.py --ponte ws://<ip-do-jetson>:8765 --robo go2
```

Aqui já funciona de ponta a ponta, com a webcam no lugar dos óculos. Serve para calibrar gestos e limiares.

**4. Trocar a webcam pelos óculos.**

1. Cadastro no Wearables Developer Center e Developer Mode nos óculos (app Meta AI).
2. Rodar o app de exemplo `meta-wearables-dat-android` e ver o vídeo dos óculos no celular. Sem os óculos, usar o MockDeviceKit.
3. No callback de frame, passar cada frame para o MediaPipe Gesture Recognizer (Android, `LIVE_STREAM`) e reaproveitar a lógica de `gesto_webcam.py`.
4. Medir a latência gesto -> robô. Se passar de ~1 s, baixar a resolução do stream (360p basta para a mão) e subir o fps.

Depois disso, o G1 é `--robo g1`, no pórtico nos primeiros testes.

## Simulação

O `unitree_mujoco` só aceita baixo nível, então `Hello()` e `WaveHand()` não existem lá. Testar sem robô exige uma política de locomoção e um modo `--robo sim` na ponte, que ainda não existe (ver [O que falta](../docs/arquitetura.md#o-que-falta)). Até lá, `--robo mock` cobre o protocolo.

## Estado

- A ponte foi testada só em modo `mock`: protocolo, cooldown, ação recusada e parada por heartbeat funcionaram.
- As classes Go2 e G1 seguem os exemplos oficiais do SDK, mas não rodaram num robô.
- `gesto_webcam.py` compila, mas não foi executado com webcam.

## Segurança

- Controle físico na mão de outra pessoa durante os testes.
- Só a lista fechada de ações é aceita.
- Desconexão do celular -> `StopMove`.
- No G1, a ponte nunca chama `Damp` (ele cai).
