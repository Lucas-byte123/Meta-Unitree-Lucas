"""Cliente de teclado para testar a ponte sem gestos: digite a ação e Enter."""
import asyncio, json, sys, uuid
import websockets

async def main(url):
    async with websockets.connect(url) as ws:
        print("ações: cumprimentar, sentar, levantar, alongar, high_five, palmas, soltar_braco, parar (Ctrl+C sai)")
        while True:
            acao = (await asyncio.to_thread(input, "> ")).strip()
            if acao:
                await ws.send(json.dumps({"tipo": "acao", "acao": acao, "id": uuid.uuid4().hex[:8]}))
                print(await ws.recv())

asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "ws://localhost:8765"))
