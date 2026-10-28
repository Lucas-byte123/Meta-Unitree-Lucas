"""Reconhece gestos na webcam (ou num vídeo gravado) e manda as ações para a ponte.

Serve para validar gesto -> ponte -> robô ANTES de ter o app Android. O app vai
fazer a mesma coisa, trocando a webcam pelo vídeo dos óculos (Meta DAT).

Uso (dentro de mvp-gesto/, com o ambiente virtual ativo):
    python gesto_webcam.py                              # webcam -> ponte em ws://localhost:8765
    python gesto_webcam.py --ponte nenhuma              # só reconhece, sem ponte
    python gesto_webcam.py --video gestos.mp4 --ponte nenhuma --log gestos.csv
    python gesto_webcam.py --ponte ws://192.168.0.50:8765 --robo go2

Teclas na janela: q ou Esc para sair.
"""
import argparse
import asyncio
import csv
import json
import time
import urllib.request
import uuid
from collections import Counter
from pathlib import Path

import cv2
import mediapipe as mp

from filtro import CONFIANCA_MIN, CONFIANCA_MIN_PARAR, FiltroGesto

# Gestos prontos do MediaPipe: Closed_Fist, Open_Palm, Pointing_Up,
# Thumb_Down, Thumb_Up, Victory, ILoveYou.
MAPA = {
    "go2": {"Thumb_Up": "cumprimentar", "Victory": "sentar", "Pointing_Up": "levantar", "Open_Palm": "parar"},
    "g1": {"Thumb_Up": "cumprimentar", "Victory": "high_five", "ILoveYou": "palmas", "Open_Palm": "parar"},
}
HEARTBEAT_S = 0.1
AQUI = Path(__file__).resolve().parent
URL_MODELO = ("https://storage.googleapis.com/mediapipe-models/gesture_recognizer/"
              "gesture_recognizer/float16/1/gesture_recognizer.task")

VERDE, AMARELO, VERMELHO, BRANCO, PRETO = (80, 200, 80), (0, 200, 255), (60, 60, 230), (255, 255, 255), (0, 0, 0)


def carregar_reconhecedor(caminho):
    caminho = Path(caminho)
    if not caminho.exists():
        print(f"Baixando o modelo de gestos para {caminho} ...")
        urllib.request.urlretrieve(URL_MODELO, caminho)
    opts = mp.tasks.vision.GestureRecognizerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(caminho)),
        running_mode=mp.tasks.vision.RunningMode.VIDEO,
    )
    return mp.tasks.vision.GestureRecognizer.create_from_options(opts)


class Painel:
    """Estado mostrado na tela e no resumo final."""

    def __init__(self, com_ponte):
        self.ponte = "conectada" if com_ponte else "sem ponte"
        self.ultima = "-"
        self.cor_ultima = BRANCO
        self.disparos = Counter()
        self.recusas = Counter()
        self.quadros_por_gesto = Counter()


async def ler_respostas(ws, painel):
    """Lê os acks da ponte em paralelo, sem travar o loop da câmera."""
    import websockets
    try:
        async for bruto in ws:
            r = json.loads(bruto)
            acao = r.get("acao") or "?"
            if r.get("ok"):
                painel.ultima, painel.cor_ultima = f"{acao}: ok", VERDE
            else:
                painel.ultima, painel.cor_ultima = f"recusado: {r.get('erro')}", VERMELHO
                painel.recusas[r.get("erro")] += 1
            print("  ponte:", r)
    except websockets.ConnectionClosed:
        pass
    painel.ponte = "desconectada"


def desenhar(frame, resultado, gesto, conf, filtro, t_ms, painel, fps, espelhar):
    h, w = frame.shape[:2]
    for mao in resultado.hand_landmarks:
        for p in mao:
            cv2.circle(frame, (int(p.x * w), int(p.y * h)), 3, AMARELO, -1)
    if espelhar:
        frame = cv2.flip(frame, 1)

    cv2.rectangle(frame, (0, 0), (w, 92), PRETO, -1)
    no_mapa = gesto in filtro.mapa
    cor = VERDE if no_mapa and filtro.vale(gesto, conf) else BRANCO
    # sem acentos: o putText do OpenCV não desenha caracteres fora do ASCII
    texto = f"{gesto} {conf:.2f}" if gesto else ("mao sem gesto" if resultado.hand_landmarks else "sem mao")
    if no_mapa:
        texto += f"  -> {filtro.mapa[gesto]}"
    cv2.putText(frame, texto, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, cor, 2)
    progresso = filtro.progresso(t_ms)
    if progresso > 0:
        cv2.rectangle(frame, (10, 38), (10 + int(200 * progresso), 46), VERDE, -1)
        cv2.rectangle(frame, (10, 38), (210, 46), BRANCO, 1)
    cv2.putText(frame, f"ultima: {painel.ultima}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, painel.cor_ultima, 1)
    cv2.putText(frame, f"ponte: {painel.ponte}   {fps:.0f} fps", (10, 88), cv2.FONT_HERSHEY_SIMPLEX, 0.5, BRANCO, 1)
    return frame


def resumo(painel, quadros, duracao_s, do_video):
    print("\n=== Resumo ===")
    origem = "do vídeo" if do_video else "de captura"
    print(f"Quadros: {quadros} em {duracao_s:.1f} s {origem} ({quadros / max(duracao_s, 1e-6):.1f} fps)")
    print(f"Quadros por gesto (confiança >= {CONFIANCA_MIN}, ou >= {CONFIANCA_MIN_PARAR} no parar):")
    for g, n in painel.quadros_por_gesto.most_common():
        print(f"  {g:12s} {n:6d}  ({100 * n / max(quadros, 1):.0f}%)")
    print("Ações disparadas:", dict(painel.disparos) or "nenhuma")
    if painel.recusas:
        print("Recusadas pela ponte:", dict(painel.recusas))


async def main():
    ap = argparse.ArgumentParser(description="Gestos da webcam ou de um vídeo -> ponte")
    ap.add_argument("--ponte", default="ws://localhost:8765", help='endereço da ponte, ou "nenhuma"')
    ap.add_argument("--robo", choices=list(MAPA), default="go2", help="qual mapa de gestos usar")
    ap.add_argument("--camera", type=int, default=0, help="índice da webcam")
    ap.add_argument("--video", help="arquivo de vídeo no lugar da webcam (ex.: gravado com os óculos)")
    ap.add_argument("--modelo", default=str(AQUI / "gesture_recognizer.task"))
    ap.add_argument("--log", help="CSV com o gesto de cada quadro, para medir depois")
    ap.add_argument("--sem-janela", action="store_true", help="não abre janela (útil para vídeos)")
    a = ap.parse_args()

    filtro = FiltroGesto(MAPA[a.robo])
    rec = carregar_reconhecedor(a.modelo)
    cap = cv2.VideoCapture(a.video if a.video else a.camera)
    if not cap.isOpened():
        fonte = a.video or f"webcam {a.camera}"
        raise SystemExit(f"Não consegui abrir {fonte}. No Mac, libere a câmera para o Terminal em "
                         "Ajustes do Sistema > Privacidade e Segurança > Câmera.")

    ws = None
    if a.ponte != "nenhuma":
        import websockets
        try:
            ws = await websockets.connect(a.ponte, open_timeout=3)
        except (OSError, asyncio.TimeoutError) as e:
            raise SystemExit(f"Não achei a ponte em {a.ponte} ({e}).\n"
                             "Rode em outro terminal: python ponte.py --robo mock\n"
                             "Ou rode sem ponte: python gesto_webcam.py --ponte nenhuma")
    painel = Painel(ws is not None)
    leitor = asyncio.create_task(ler_respostas(ws, painel)) if ws else None

    arq_log = open(a.log, "w", newline="") if a.log else None
    escritor = csv.writer(arq_log) if arq_log else None
    if escritor:
        escritor.writerow(["t_ms", "gesto", "confianca", "acao"])

    t0 = time.monotonic()
    ultimo_ts, ultimo_hb, quadros = -1, 0.0, 0
    fps, t_fps, quadros_fps = 0.0, t0, 0
    print("Rodando. q ou Esc na janela para sair." if not a.sem_janela else "Rodando...")
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            agora = time.monotonic()
            quadros += 1
            # tempo do quadro: do próprio vídeo, ou do relógio na webcam
            ts = int(cap.get(cv2.CAP_PROP_POS_MSEC)) if a.video else int((agora - t0) * 1000)
            ts = max(ts, ultimo_ts + 1)  # o MediaPipe exige tempo sempre crescente
            ultimo_ts = ts
            if a.video and ws:
                # com ponte, o vídeo roda em tempo real: a ponte mede o relógio (cooldown, heartbeat)
                await asyncio.sleep(max(0.0, ts / 1000 - (agora - t0)))
                agora = time.monotonic()

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            r = rec.recognize_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ts)
            gesto, conf = None, 0.0
            if r.gestures:
                melhor = r.gestures[0][0]
                gesto, conf = melhor.category_name, melhor.score
                if gesto == "None":  # o MediaPipe chama de "None" uma mão sem gesto conhecido
                    gesto = None
            if filtro.vale(gesto, conf):
                painel.quadros_por_gesto[gesto] += 1

            acao = filtro.atualizar(gesto, conf, ts)
            if acao:
                painel.disparos[acao] += 1
                print(f"[{ts / 1000:7.2f} s] {gesto} -> {acao}")
                if not ws:
                    painel.ultima, painel.cor_ultima = f"{acao} (sem ponte)", AMARELO
            if escritor:
                escritor.writerow([ts, gesto or "", f"{conf:.3f}", acao or ""])

            if ws and painel.ponte == "conectada":
                try:
                    if agora - ultimo_hb >= HEARTBEAT_S:
                        await ws.send(json.dumps({"tipo": "heartbeat"}))
                        ultimo_hb = agora
                    if acao:
                        await ws.send(json.dumps({"tipo": "acao", "acao": acao, "id": uuid.uuid4().hex[:8]}))
                except Exception:
                    painel.ponte = "desconectada"

            quadros_fps += 1
            if agora - t_fps >= 1.0:
                fps, t_fps, quadros_fps = quadros_fps / (agora - t_fps), agora, 0

            if not a.sem_janela:
                tela = desenhar(frame, r, gesto, conf, filtro, ts, painel, fps, espelhar=not a.video)
                cv2.imshow("gesto -> ponte", tela)
                if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                    break
            await asyncio.sleep(0)  # deixa a leitura dos acks rodar
    finally:
        duracao = ultimo_ts / 1000 if a.video else time.monotonic() - t0
        resumo(painel, quadros, duracao, bool(a.video))
        cap.release()
        cv2.destroyAllWindows()
        if arq_log:
            arq_log.close()
            print("Log salvo em", a.log)
        if ws:
            await ws.close()
        if leitor:
            leitor.cancel()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
