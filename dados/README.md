# Dados de teste

CSVs gravados pelo app Android ([`app-android`](../app-android/README.md#medir-o-que-o-mediapipe-viu)): uma linha por quadro, `t_ms,gesto,confianca,tem_mao,acao`. `t_ms` é o relógio do celular (`SystemClock.uptimeMillis`), não a hora do dia. `confianca` sem `gesto` é a confiança de "mão sem gesto conhecido".

Celular: Galaxy S25+ (Android 17), pelo cabo, com a ponte em `mock`. Em cada rodada, uma tentativa de cada gesto, na ordem 👍 ✌️ ☝️ ✋, ~5 s cada.

| Arquivo | Data | Limiar | O que tem | Resultado |
|---|---|---|---|---|
| `gestos-20261028-181846.csv` | 28/10/2026 | 0,7 | Rodada 1: câmera frontal, palma para a câmera (~293–337 s). Rodada 2: câmera traseira, primeira pessoa (~351–384 s) | 2 de 4 nas duas rodadas. 👍 e ✋ ficam entre 0,6 e 0,7; ✋ não disparou nenhuma vez |
| `gestos-20261029-151536.csv` | 29/10/2026 | 0,65, e 0,55 no parar | As mesmas duas rodadas (~230–252 s e ~264–283 s) | 4 de 4 nas duas. Na rodada 2, o ✌️ foi recusado pela ponte (`ocupado`, cooldown de 3 s) |
| `gestos-20261029-152044.csv` | 29/10/2026 | 0,65 / 0,55 | Começo do teste dos 5 minutos sem disparo falso; só 27 s | Nenhum disparo, mas curto demais para valer |

Foram esses dados que levaram à troca do limiar de 0,7 para 0,65 / 0,55 no `filtro.py` e no `FiltroGesto.kt`.

Para resumir um CSV em trechos com a mão visível (gesto, confiança média e máxima, ações disparadas):

```
python3 dados/episodios.py dados/gestos-20261029-151536.csv
```

Para repassar um CSV pelo filtro atual, sem celular: ler as linhas e chamar `FiltroGesto(MAPA["go2"]).atualizar(gesto, confianca, t_ms)` de `mvp-gesto/filtro.py`.
