"""Ponte WebSocket -> robô Unitree (MVP "um gesto, uma ação").

Roda no computador de bordo do robô (Jetson). Recebe mensagens JSON do
celular (ou do cliente de teste no laptop) e chama o SDK da Unitree.

Uso:
    python3 ponte.py --robo mock                 # sem robô, só imprime
    python3 ponte.py --robo go2 --iface eth0
    python3 ponte.py --robo g1  --iface eth0

Protocolo (uma mensagem JSON por frame WebSocket):
    {"tipo": "acao", "acao": "cumprimentar", "id": "abc123"}
    {"tipo": "acao", "acao": "parar"}
    {"tipo": "heartbeat"}
Resposta:
    {"tipo": "ack", "id": "abc123", "ok": true, "acao": "cumprimentar"}
"""
import argparse
import asyncio
import json
import logging
import time

import websockets

log = logging.getLogger("ponte")

COOLDOWN_S = 3.0          # tempo mínimo entre duas ações (exceto "parar")
HEARTBEAT_TIMEOUT_S = 0.3  # sem heartbeat por esse tempo -> StopMove


class RoboMock:
    def executar(self, acao):
        log.info("[mock] executaria: %s", acao)

    def parar(self):
        log.info("[mock] StopMove")


class RoboGo2:
    def __init__(self, iface):
        from unitree_sdk2py.core.channel import ChannelFactoryInitialize
        from unitree_sdk2py.go2.sport.sport_client import SportClient

        ChannelFactoryInitialize(0, iface)
        self.c = SportClient()
        self.c.SetTimeout(10.0)
        self.c.Init()
        self.acoes = {
            "cumprimentar": self.c.Hello,   # dá a pata
            "sentar": self.c.Sit,
            "levantar": self.c.RiseSit,
            "alongar": self.c.Stretch,
        }

    def executar(self, acao):
        self.acoes[acao]()

    def parar(self):
        self.c.StopMove()


class RoboG1:
    def __init__(self, iface):
        from unitree_sdk2py.core.channel import ChannelFactoryInitialize
        from unitree_sdk2py.g1.arm.g1_arm_action_client import G1ArmActionClient, action_map
        from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient

        ChannelFactoryInitialize(0, iface)
        self.loco = LocoClient()
        self.loco.SetTimeout(10.0)
        self.loco.Init()
        self.braco = G1ArmActionClient()
        self.braco.SetTimeout(10.0)
        self.braco.Init()
        m = action_map
        self.acoes = {
            "cumprimentar": lambda: self.loco.WaveHand(),
            "high_five": lambda: self.braco.ExecuteAction(m["high five"]),
            "palmas": lambda: self.braco.ExecuteAction(m["clap"]),
            "soltar_braco": lambda: self.braco.ExecuteAction(m["release arm"]),
        }

    def executar(self, acao):
        self.acoes[acao]()

    def parar(self):
        # Nunca Damp aqui: no G1 o Damp tira o torque e o humanoide cai.
        self.loco.StopMove()


class Ponte:
    def __init__(self, robo):
        self.robo = robo
        self.ultima_acao = 0.0
        self.ultimo_heartbeat = None
        self.lock = asyncio.Lock()

    def acoes_validas(self):
        return getattr(self.robo, "acoes", None) or {"cumprimentar", "sentar", "levantar", "alongar",
                                                     "high_five", "palmas", "soltar_braco"}

    async def tratar(self, msg):
        tipo = msg.get("tipo")
        if tipo == "heartbeat":
            self.ultimo_heartbeat = time.monotonic()
            return None
        if tipo != "acao":
            return {"tipo": "ack", "ok": False, "erro": "tipo desconhecido"}

        acao, mid = msg.get("acao"), msg.get("id")
        if acao == "parar":  # prioridade máxima, sem cooldown
            await asyncio.to_thread(self.robo.parar)
            return {"tipo": "ack", "id": mid, "ok": True, "acao": acao}
        if acao not in self.acoes_validas():
            return {"tipo": "ack", "id": mid, "ok": False, "erro": f"ação não permitida: {acao}"}
        if time.monotonic() - self.ultima_acao < COOLDOWN_S or self.lock.locked():
            return {"tipo": "ack", "id": mid, "ok": False, "erro": "ocupado"}

        async with self.lock:
            self.ultima_acao = time.monotonic()
            log.info("executando %s", acao)
            await asyncio.to_thread(self.robo.executar, acao)
        return {"tipo": "ack", "id": mid, "ok": True, "acao": acao}

    async def vigia_heartbeat(self):
        # Só age se algum cliente já mandou heartbeat (ações discretas funcionam sem ele).
        while True:
            await asyncio.sleep(0.1)
            if self.ultimo_heartbeat and time.monotonic() - self.ultimo_heartbeat > HEARTBEAT_TIMEOUT_S:
                log.warning("heartbeat perdido -> parar")
                await asyncio.to_thread(self.robo.parar)
                self.ultimo_heartbeat = None

    async def conexao(self, ws):
        log.info("cliente conectado: %s", ws.remote_address)
        try:
            async for bruto in ws:
                try:
                    resp = await self.tratar(json.loads(bruto))
                except Exception as e:  # erro do SDK ou JSON inválido
                    log.exception("falha")
                    resp = {"tipo": "ack", "ok": False, "erro": str(e)}
                if resp:
                    await ws.send(json.dumps(resp, ensure_ascii=False))
        finally:
            log.info("cliente desconectado -> parar")
            await asyncio.to_thread(self.robo.parar)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--robo", choices=["mock", "go2", "g1"], default="mock")
    ap.add_argument("--iface", default="eth0", help="interface da rede 192.168.123.x")
    ap.add_argument("--porta", type=int, default=8765)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    robo = {"mock": lambda: RoboMock(), "go2": lambda: RoboGo2(a.iface), "g1": lambda: RoboG1(a.iface)}[a.robo]()
    ponte = Ponte(robo)
    asyncio.create_task(ponte.vigia_heartbeat())
    async with websockets.serve(ponte.conexao, "0.0.0.0", a.porta):
        log.info("ponte ouvindo em ws://0.0.0.0:%d (robô: %s)", a.porta, a.robo)
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
