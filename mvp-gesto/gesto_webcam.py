"""Cliente de teste: reconhece gestos na webcam do laptop e manda para a ponte.

Serve para validar gesto -> ponte -> robô ANTES de ter o app Android dos óculos.
O app Android vai fazer exatamente a mesma coisa, só trocando a webcam pelo
stream de câmera dos óculos (Meta DAT).

Uso:
    pip install mediapipe opencv-python websockets
    wget https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task
    python3 gesto_webcam.py --ponte ws://192.168.123.18:8765 --robo go2
"""
import argparse
import asyncio
import json
import time
import uuid

import cv2
import mediapipe as mp
import websockets

# Gestos prontos do MediaPipe: Closed_Fist, Open_Palm, Pointing_Up,
# Thumb_Down, Thumb_Up, Victory, ILoveYou.
MAPA = {
    "go2": {"Thumb_Up": "cumprimentar", "Victory": "sentar", "Pointing_Up": "levantar", "Open_Palm": "parar"},
    "g1": {"Thumb_Up": "cumprimentar", "Victory": "high_five", "ILoveYou": "palmas", "Open_Palm": "parar"},
}
CONFIANCA_MIN = 0.7
FRAMES_ESTAVEIS = 8   # ~0,5 s a 15 fps: o gesto precisa se manter para disparar


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ponte", default="ws://localhost:8765")
    ap.add_argument("--robo", choices=list(MAPA), default="go2")
    ap.add_argument("--modelo", default="gesture_recognizer.task")
    a = ap.parse_args()
    mapa = MAPA[a.robo]

    opts = mp.tasks.vision.GestureRecognizerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=a.modelo),
        running_mode=mp.tasks.vision.RunningMode.VIDEO,
    )
    rec = mp.tasks.vision.GestureRecognizer.create_from_options(opts)
    cam = cv2.VideoCapture(0)

    async with websockets.connect(a.ponte) as ws:
        atual, contagem, disparado = None, 0, None
        while True:
            ok, frame = cam.read()
            if not ok:
                break
            img = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            r = rec.recognize_for_video(img, int(time.monotonic() * 1000))
            g = None
            if r.gestures and r.gestures[0][0].score >= CONFIANCA_MIN:
                g = r.gestures[0][0].category_name

            contagem = contagem + 1 if g == atual else 1
            atual = g
            if g in mapa and contagem >= FRAMES_ESTAVEIS and disparado != g:
                disparado = g
                msg = {"tipo": "acao", "acao": mapa[g], "id": uuid.uuid4().hex[:8]}
                await ws.send(json.dumps(msg))
                print("enviado:", msg, "| resposta:", await ws.recv())
            if g is None:
                disparado = None  # precisa baixar a mão para repetir o gesto

            cv2.putText(frame, f"{g or '-'} ({contagem})", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow("gesto", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break


if __name__ == "__main__":
    asyncio.run(main())
