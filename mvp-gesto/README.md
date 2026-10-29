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

Contra disparo acidental ([`filtro.py`](filtro.py)): confiança >= 0,65 (0,55 para "parar", porque um parar à toa só para o robô; medido no celular em 28/10/2026, 0,7 quase nunca disparava 👍 e ✋), gesto estável por 0,5 s (0,2 s para "parar"), só dispara de novo depois de baixar a mão ou trocar de gesto. A ponte ainda ignora truques por 3 s depois de cada um ("parar" nunca espera).

Além dos truques, a ponte aceita movimento: `frente`, `tras`, `girar_esq`, `girar_dir` e `{"tipo":"mover","vx":..,"vy":..,"giro":..}`. Todo movimento para sozinho depois de 1 s se não for renovado, e a velocidade é cortada em 0,3 m/s e 0,6 rad/s. Por enquanto não há gesto para movimento; dá para testar pelo `teclado.py`.

## Arquivos

| Arquivo | Onde roda | O que faz |
|---|---|---|
| `ponte.py` | Jetson do robô, ou laptop no caminho A | Servidor WebSocket; valida e chama o SDK (Go2, G1 ou mock) ou, no caminho A, a biblioteca WebRTC (`go2-webrtc`). Limita velocidade, faz movimento expirar e para o robô se o cliente cair ou o heartbeat parar. |
| `filtro.py` | Laptop (e, traduzido, o app) | Filtro anti-disparo: gesto de cada quadro -> ação. Sem dependências. |
| `gesto_webcam.py` | Laptop | MediaPipe na webcam ou num vídeo -> filtro -> ponte. Referência para o app Android. |
| `teclado.py` | Laptop | Manda ações e velocidades digitadas. |
| `checar_go2.py` | Laptop | Conecta ao Go2 por WebRTC e lê o modo de movimento, sem mover nada. Primeiro passo da sessão com o robô. |
| `tests/` | Laptop | Testes do filtro e da ponte, sem robô e sem câmera. |

Instalação (Python 3.11; o MediaPipe ainda não tem versão para o 3.14):

```
cd mvp-gesto
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest          # 42 testes, ~4 s
```

O modelo de gestos (`gesture_recognizer.task`) é baixado sozinho na primeira execução do `gesto_webcam.py`.

O `unitree_sdk2_python` só é necessário no Jetson ([instalação](https://github.com/unitreerobotics/unitree_sdk2_python)).

## Etapas

Cada uma dá para testar sozinha.

**1. Robô obedece a um script.** SSH no Jetson, instalar `unitree_sdk2_python`, rodar `example/go2/high_level/go2_sport_client.py <iface>`. Pronto quando o Go2 der a pata a partir do terminal.

**2. Ponte + teclado.** No Jetson: `python3 ponte.py --robo go2 --iface <iface>`. No laptop, no mesmo Wi-Fi: `python3 teclado.py ws://<ip-do-jetson>:8765` e digitar `cumprimentar`. Sem robô: `--robo mock`.

**2-A. Ponte no laptop pelo Wi-Fi (caminho A).** Sem SSH nem Jetson: a ponte fala com o Go2 por WebRTC, com a [unitree_webrtc_connect](https://github.com/legion1581/unitree_webrtc_connect).

```
brew install portaudio                       # no Mac; no Linux: sudo apt install portaudio19-dev
pip install -r requirements-webrtc.txt
unitree-fetch-aes-key --email <conta Unitree do robô> --password '...' --device-type Go2   # firmware >= 1.1.15
export UNITREE_AES_128_KEY=<chave>           # nunca em arquivo do repositório
python ponte.py --robo go2-webrtc --ip <ip-do-go2>          # robô e laptop no mesmo roteador
python ponte.py --robo go2-webrtc --modo ap                  # ou: laptop no Wi-Fi do próprio robô
```

O robô precisa estar de pé e no modo normal (pelo controle ou pelo app da Unitree): a ponte não troca o modo. **Não rode os exemplos da biblioteca como vêm:** o `sportmode.py` anda a 0,5 m/s e manda o robô plantar bananeira.

Escrito e testado com uma imitação da biblioteca (`tests/test_go2_webrtc.py`); **ainda não rodou num robô.**

**3. Gesto na webcam -> robô.** Primeiro com a ponte em `mock` no próprio laptop (roteiro abaixo), depois com `--ponte ws://<ip-da-ponte>:8765`.

Aqui já funciona de ponta a ponta, com a webcam no lugar dos óculos. Serve para calibrar gestos e limiares.

**4. Trocar a webcam pelos óculos.**

1. Cadastro no Wearables Developer Center e Developer Mode nos óculos (app Meta AI).
2. Rodar o app de exemplo `meta-wearables-dat-android` e ver o vídeo dos óculos no celular. Sem os óculos, usar o MockDeviceKit.
3. No callback de frame, passar cada frame para o MediaPipe Gesture Recognizer (Android, `LIVE_STREAM`) e reaproveitar a lógica de `gesto_webcam.py`.
4. Medir a latência gesto -> robô. Se passar de ~1 s, baixar a resolução do stream (360p basta para a mão) e subir o fps.

Depois disso, o G1 é `--robo g1`, no pórtico nos primeiros testes.

## Teste com a webcam, sem robô

`--robo mock` cobre o protocolo e as regras de parada sem mover nada. Dois terminais, os dois em `mvp-gesto/` com `source .venv/bin/activate`:

```
# terminal 1
python ponte.py --robo mock

# terminal 2
python gesto_webcam.py
```

Na primeira vez o macOS pede acesso à câmera para o Terminal (ou libere em Ajustes do Sistema > Privacidade e Segurança > Câmera). Na janela: o gesto e a confiança, a barra enchendo até disparar, a resposta da ponte. `q` ou `Esc` sai e mostra um resumo.

O que conferir (checkpoints da F2 do [plano](../docs/plano.md#f2-gesto-pela-webcam---go2)):

- [ ] Cada gesto do mapa (`Thumb_Up`, `Victory`, `Pointing_Up`, `Open_Palm`) dispara em pelo menos 9 de 10 tentativas, e o terminal 1 mostra `[mock] executaria: ...`.
- [ ] Segurar o gesto não repete a ação; baixar a mão e repetir dispara de novo.
- [ ] Mão aberta dispara `parar` rápido (~0,2 s).
- [ ] 5 minutos mexendo as mãos normalmente (digitando, falando) sem nenhuma ação disparada. Use `--log teste.csv` para guardar o que foi visto.
- [ ] Fechar o `gesto_webcam.py` com o terminal 1 aberto: a ponte mostra `cliente desconectado -> parar`.
- [ ] Com `python teclado.py` no lugar do terminal 2: `frente` anda e para sozinho em 1 s; `mover 2 0 0` volta cortado para 0,3.

Outros modos úteis:

```
python gesto_webcam.py --ponte nenhuma                       # só reconhecimento
python gesto_webcam.py --video gravado.mp4 --ponte nenhuma --log gravado.csv   # vídeos dos óculos (semana 2)
```

## Estado

- Testes do filtro e da ponte passando (`python -m unittest`).
- Testado de ponta a ponta sem webcam: um vídeo montado com fotos de exemplo do MediaPipe passou pelo `gesto_webcam.py` com o MediaPipe real até a ponte em `mock` (3 truques aceitos, gesto fora do mapa ignorado), e um cliente WebSocket conferiu expiração do movimento, limite de velocidade, ação recusada e parada por heartbeat.
- Testado com a webcam ao vivo em 12/10/2026, com a ponte em `mock`: o roteiro acima funcionou.
- **Ainda não rodou num robô.** As classes Go2 e G1 seguem os exemplos oficiais do SDK.

## Segurança

- Controle físico na mão de outra pessoa durante os testes.
- Só a lista fechada de ações é aceita.
- Desconexão do celular ou heartbeat perdido -> `StopMove`.
- Todo movimento expira em 1 s e a velocidade é limitada na ponte.
- No G1, a ponte nunca chama `Damp` (ele cai).
