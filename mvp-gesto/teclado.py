"""Cliente de teclado para testar a ponte sem gestos: digite a ação e Enter.

    python teclado.py                        # ponte em ws://localhost:8765
    python teclado.py ws://192.168.0.50:8765

Manda heartbeat a cada 100 ms, como o app: o vigia da ponte fica ativo e para o
robô se o heartbeat sumir por 0,3 s.

Exemplos: cumprimentar | frente | girar_esq | parar | mover 0.2 0 0 (vx vy giro)

Testes de parada (roteiro da 1ª sessão em docs/plano.md). Um "frente" dura só 1 s,
pouco para digitar outra coisa no meio, então cada teste é um comando só:
    segurar frente 3   renova o frente por até 3 s: dá tempo de derrubar algo no meio
    teste_heartbeat    anda e, 0,3 s depois, corta o heartbeat por 2 s sem fechar a conexão
Qualquer linha nova interrompe os dois, e "parar" sempre passa.
"""
import asyncio
import json
import os
import sys
import threading
import time
import uuid

import websockets

HEARTBEAT_S = 0.1            # igual ao app
DURACAO_NA_PONTE_S = 1.0     # DURACAO_MOVIMENTO_S da ponte
RENOVAR_S = 0.5              # renova antes de o movimento acabar na ponte
SEGURAR_MAX_S = 3.0          # 0,6 m a 0,2 m/s: curto, até saber o que o robô faz numa queda
ESPERA_TESTE_S = 0.3         # robô andando antes de cortar o heartbeat
PAUSA_HEARTBEAT_S = 2.0
MOVIMENTOS = {"frente", "tras", "girar_esq", "girar_dir"}

AJUDA = ("truques: cumprimentar, sentar, levantar, alongar, high_five, palmas, soltar_braco\n"
         "movimento (1 s, renove para continuar): frente, tras, girar_esq, girar_dir\n"
         "velocidade livre: mover vx vy giro   (ex.: mover 0.2 0 0)\n"
         f"testes de parada: segurar frente 3 (até {SEGURAR_MAX_S:.0f} s)  |  teste_heartbeat\n"
         "parar a qualquer momento: parar   |   Ctrl+C sai (e a ponte para o robô)")


def novo_id():
    return uuid.uuid4().hex[:8]


def montar(linha):
    partes = linha.split()
    if partes[0] == "mover":
        try:
            vx, vy, giro = (list(map(float, partes[1:])) + [0.0, 0.0, 0.0])[:3]
        except ValueError:
            raise ValueError("use números: mover 0.2 0 0") from None
        return {"tipo": "mover", "vx": vx, "vy": vy, "giro": giro, "id": novo_id()}
    return {"tipo": "acao", "acao": partes[0], "id": novo_id()}


def ler_segurar(linha):
    """'segurar frente 2' -> ('frente', 2.0). O tempo é cortado em SEGURAR_MAX_S."""
    partes = linha.split()
    if len(partes) < 2 or partes[1] not in MOVIMENTOS:
        raise ValueError(f"use: segurar <{'|'.join(sorted(MOVIMENTOS))}> [segundos]")
    try:
        segundos = float(partes[2]) if len(partes) > 2 else SEGURAR_MAX_S
    except ValueError:
        raise ValueError("o tempo é um número de segundos: segurar frente 2") from None
    if not segundos > 0:
        raise ValueError("o tempo precisa ser maior que zero")
    return partes[1], min(segundos, SEGURAR_MAX_S)


def escrever_na_tela(texto):
    # o "> " do input continua esperando enquanto as respostas chegam
    print(f"\r{texto}\n> ", end="", flush=True)


class Teclado:
    def __init__(self, ws, escrever=escrever_na_tela):
        self.ws = ws
        self.escrever = escrever
        self.heartbeat_ligado = True
        self.tarefa = None  # segurar ou teste_heartbeat em andamento

    async def enviar(self, msg):
        await self.ws.send(json.dumps(msg))

    async def heartbeat(self):
        try:
            while True:
                if self.heartbeat_ligado:
                    await self.enviar({"tipo": "heartbeat"})
                await asyncio.sleep(HEARTBEAT_S)
        except websockets.ConnectionClosed:
            pass

    async def mostrar_respostas(self):
        try:
            async for bruto in self.ws:
                r = json.loads(bruto)
                if r.get("id") or not r.get("ok"):  # as renovações do segurar vão sem id
                    self.escrever(bruto)
        except websockets.ConnectionClosed:
            pass

    def iniciar(self, corotina):
        self.interromper()
        self.tarefa = asyncio.create_task(corotina)

    def interromper(self):
        if self.tarefa and not self.tarefa.done():
            self.tarefa.cancel()
        self.tarefa = None

    async def segurar(self, acao, segundos):
        inicio = time.monotonic()
        await self.enviar({"tipo": "acao", "acao": acao, "id": novo_id()})
        while True:
            await asyncio.sleep(RENOVAR_S)
            if time.monotonic() - inicio + DURACAO_NA_PONTE_S > segundos:
                break
            await self.enviar({"tipo": "acao", "acao": acao})
        self.escrever(f"segurar {acao}: fim das renovações; a ponte para o robô em até {DURACAO_NA_PONTE_S:.0f} s")

    async def teste_heartbeat(self):
        await self.enviar({"tipo": "acao", "acao": "frente", "id": novo_id()})
        await asyncio.sleep(ESPERA_TESTE_S)
        self.heartbeat_ligado = False
        self.escrever(f"heartbeat cortado por {PAUSA_HEARTBEAT_S:.0f} s. Esperado no log da ponte: "
                      "'heartbeat perdido -> parar', e não 'movimento expirou'")
        try:
            await asyncio.sleep(PAUSA_HEARTBEAT_S)
        finally:
            self.heartbeat_ligado = True
        self.escrever("heartbeat de volta")

    async def tratar_linha(self, linha):
        comando = linha.split()[0]
        if comando == "segurar":
            self.iniciar(self.segurar(*ler_segurar(linha)))
        elif comando == "teste_heartbeat":
            self.iniciar(self.teste_heartbeat())
        else:
            await self.enviar(montar(linha))


def ler_linhas(loop, fila):
    """Lê o teclado numa thread à parte. É daemon para não segurar a saída no Ctrl+C."""
    while True:
        try:
            linha = input("> ")
        except EOFError:
            linha = None
        loop.call_soon_threadsafe(fila.put_nowait, linha)
        if linha is None:
            return


async def main(url):
    try:
        ws = await websockets.connect(url)
    except OSError as e:
        print(f"Não achei a ponte em {url}: {e}")
        return
    async with ws:
        t = Teclado(ws)
        print(AJUDA)
        fila = asyncio.Queue()
        threading.Thread(target=ler_linhas, args=(asyncio.get_running_loop(), fila), daemon=True).start()
        batimento = asyncio.create_task(t.heartbeat())
        respostas = asyncio.create_task(t.mostrar_respostas())
        try:
            while True:
                proxima = asyncio.create_task(fila.get())
                await asyncio.wait({proxima, respostas}, return_when=asyncio.FIRST_COMPLETED)
                if not proxima.done():
                    proxima.cancel()
                    print("\nA ponte fechou a conexão.")
                    return
                linha = proxima.result()
                if linha is None:
                    return
                if not linha.strip():
                    continue
                t.interromper()  # qualquer linha nova interrompe o segurar ou o teste
                try:
                    await t.tratar_linha(linha.strip())
                except ValueError as e:
                    t.escrever(str(e))
        finally:
            t.interromper()
            batimento.cancel()
            respostas.cancel()
            # fechamento normal (1000); saindo pelo Ctrl+C, o "async with" fecharia com 1011
            # (erro interno) e a ponte registraria um traceback à toa
            await ws.close()


if __name__ == "__main__":
    try:
        asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "ws://localhost:8765"))
    except KeyboardInterrupt:
        pass
    # a thread do input() continua presa no stdin e atrasaria a saída: sai sem esperar por ela
    sys.stdout.flush()
    os._exit(0)
