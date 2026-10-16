"""Cliente de teclado para testar a ponte sem gestos: digite a ação e Enter.

    python teclado.py                        # ponte em ws://localhost:8765
    python teclado.py ws://192.168.0.50:8765

Exemplos: cumprimentar | frente | girar_esq | parar | mover 0.2 0 0 (vx vy giro)
"""
import asyncio, json, sys, uuid
import websockets

AJUDA = ("truques: cumprimentar, sentar, levantar, alongar, high_five, palmas, soltar_braco\n"
         "movimento (1 s, renove para continuar): frente, tras, girar_esq, girar_dir\n"
         "velocidade livre: mover vx vy giro   (ex.: mover 0.2 0 0)\n"
         "parar a qualquer momento: parar   |   Ctrl+C sai")


def montar(linha):
    partes = linha.split()
    if partes[0] == "mover":
        vx, vy, giro = (list(map(float, partes[1:])) + [0.0, 0.0, 0.0])[:3]
        return {"tipo": "mover", "vx": vx, "vy": vy, "giro": giro, "id": uuid.uuid4().hex[:8]}
    return {"tipo": "acao", "acao": partes[0], "id": uuid.uuid4().hex[:8]}


async def main(url):
    async with websockets.connect(url) as ws:
        print(AJUDA)
        while True:
            linha = (await asyncio.to_thread(input, "> ")).strip()
            if not linha:
                continue
            try:
                msg = montar(linha)
            except ValueError:
                print("use números: mover 0.2 0 0")
                continue
            await ws.send(json.dumps(msg))
            print(await ws.recv())


try:
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "ws://localhost:8765"))
except KeyboardInterrupt:
    pass
