"""Ponte WebSocket -> robô Unitree (MVP "um gesto, uma ação").

Recebe mensagens JSON do celular (ou dos clientes de teste no laptop) e chama
o SDK da Unitree. É também o filtro de segurança: só aceita ações conhecidas,
limita a velocidade, faz todo movimento expirar e para o robô se o cliente sumir.

Uso:
    python3 ponte.py --robo mock                 # sem robô, só imprime
    python3 ponte.py --robo go2 --iface eth0
    python3 ponte.py --robo g1  --iface eth0

Protocolo (uma mensagem JSON por frame WebSocket):
    {"tipo": "acao", "acao": "cumprimentar", "id": "abc123"}
    {"tipo": "acao", "acao": "frente"}            # anda por DURACAO_MOVIMENTO_S
    {"tipo": "acao", "acao": "parar"}
    {"tipo": "mover", "vx": 0.2, "vy": 0, "giro": 0}   # velocidade livre, com limite
    {"tipo": "heartbeat"}
Resposta:
    {"tipo": "ack", "id": "abc123", "ok": true, "acao": "cumprimentar"}
"""
import argparse
import asyncio
import concurrent.futures
import json
import logging
import math
import time

log = logging.getLogger("ponte")

COOLDOWN_S = 3.0             # tempo mínimo entre dois truques (não vale para movimento nem parar)
HEARTBEAT_TIMEOUT_S = 0.3    # sem heartbeat por esse tempo -> StopMove
DURACAO_MOVIMENTO_S = 1.0    # todo movimento para sozinho se não for renovado
REENVIO_MOVIMENTO_S = 0.1    # reenvia o comando de velocidade enquanto o movimento vale
VEL_MAX_LINEAR = 0.3         # m/s, vale para vx e vy
VEL_MAX_GIRO = 0.6           # rad/s

VEL_PADRAO = 0.2
GIRO_PADRAO = 0.5
MOVIMENTOS = {
    "frente": (VEL_PADRAO, 0.0, 0.0),
    "tras": (-VEL_PADRAO, 0.0, 0.0),
    "girar_esq": (0.0, 0.0, GIRO_PADRAO),
    "girar_dir": (0.0, 0.0, -GIRO_PADRAO),
}


def limitar(vx, vy, giro):
    """Corta as velocidades nos limites. Devolve (vx, vy, giro, foi_limitado)."""
    def corta(v, m):
        return max(-m, min(m, v))
    novo = (corta(vx, VEL_MAX_LINEAR), corta(vy, VEL_MAX_LINEAR), corta(giro, VEL_MAX_GIRO))
    return (*novo, novo != (vx, vy, giro))


class RoboMock:
    TRUQUES = {"cumprimentar", "sentar", "levantar", "alongar", "high_five", "palmas", "soltar_braco"}

    def __init__(self):
        self.chamadas = []  # usado pelos testes

    def executar(self, acao):
        self.chamadas.append(("executar", acao))
        log.info("[mock] executaria: %s", acao)

    def mover(self, vx, vy, giro):
        if not self.chamadas or self.chamadas[-1] != ("mover", vx, vy, giro):
            log.info("[mock] Move(vx=%.2f, vy=%.2f, giro=%.2f)", vx, vy, giro)
        self.chamadas.append(("mover", vx, vy, giro))

    def parar(self):
        self.chamadas.append(("parar",))
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
        self.TRUQUES = set(self.acoes)

    def executar(self, acao):
        self.acoes[acao]()

    def mover(self, vx, vy, giro):
        self.c.Move(vx, vy, giro)

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
        self.TRUQUES = set(self.acoes)

    def executar(self, acao):
        self.acoes[acao]()

    def mover(self, vx, vy, giro):
        self.loco.Move(vx, vy, giro)

    def parar(self):
        # Nunca Damp aqui: no G1 o Damp tira o torque e o humanoide cai.
        self.loco.StopMove()


class Ponte:
    def __init__(self, robo):
        self.robo = robo
        self.ultimo_truque = -math.inf
        self.ultimo_heartbeat = None
        self.truque_em_andamento = asyncio.Lock()
        self.movimento = None  # tarefa que mantém o movimento atual e o faz expirar
        # mover e parar passam por uma fila de uma thread só, para chegarem ao robô
        # na ordem em que foram pedidos (um mover atrasado nunca chega depois do parar)
        self._fila_movimento = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    async def _na_fila(self, fn, *args):
        await asyncio.get_running_loop().run_in_executor(self._fila_movimento, fn, *args)

    def acoes_validas(self):
        return set(self.robo.TRUQUES) | set(MOVIMENTOS) | {"parar"}

    def em_movimento(self):
        return self.movimento is not None and not self.movimento.done()

    async def parar(self):
        if self.em_movimento():
            self.movimento.cancel()
        self.movimento = None
        await self._na_fila(self.robo.parar)

    async def _manter_movimento(self, vx, vy, giro):
        fim = time.monotonic() + DURACAO_MOVIMENTO_S
        try:
            while time.monotonic() < fim:
                await self._na_fila(self.robo.mover, vx, vy, giro)
                await asyncio.sleep(REENVIO_MOVIMENTO_S)
        except asyncio.CancelledError:
            return  # outro movimento ou um parar assumiu
        log.info("movimento expirou -> parar")
        self.movimento = None
        await self._na_fila(self.robo.parar)

    def _iniciar_movimento(self, vx, vy, giro):
        if self.em_movimento():
            self.movimento.cancel()  # renovação: o novo comando substitui o anterior
        self.movimento = asyncio.create_task(self._manter_movimento(vx, vy, giro))

    async def tratar(self, msg):
        tipo = msg.get("tipo")
        mid = msg.get("id")
        if tipo == "heartbeat":
            self.ultimo_heartbeat = time.monotonic()
            return None
        if tipo == "mover":
            return await self._tratar_mover(msg, mid)
        if tipo != "acao":
            return {"tipo": "ack", "id": mid, "ok": False, "erro": "tipo desconhecido"}

        acao = msg.get("acao")
        if acao == "parar":  # prioridade máxima, sem cooldown
            await self.parar()
            return {"tipo": "ack", "id": mid, "ok": True, "acao": acao}
        if acao not in self.acoes_validas():
            return {"tipo": "ack", "id": mid, "ok": False, "erro": f"ação não permitida: {acao}"}
        if self.truque_em_andamento.locked():
            return {"tipo": "ack", "id": mid, "ok": False, "erro": "ocupado"}

        if acao in MOVIMENTOS:
            vx, vy, giro, _ = limitar(*MOVIMENTOS[acao])
            self._iniciar_movimento(vx, vy, giro)
            return {"tipo": "ack", "id": mid, "ok": True, "acao": acao}

        # truque (dar a pata, sentar...): espera o cooldown e não roda com o robô andando
        if self.em_movimento():
            return {"tipo": "ack", "id": mid, "ok": False, "erro": "em movimento"}
        if time.monotonic() - self.ultimo_truque < COOLDOWN_S:
            return {"tipo": "ack", "id": mid, "ok": False, "erro": "ocupado"}
        async with self.truque_em_andamento:
            self.ultimo_truque = time.monotonic()
            log.info("executando %s", acao)
            await asyncio.to_thread(self.robo.executar, acao)
        return {"tipo": "ack", "id": mid, "ok": True, "acao": acao}

    async def _tratar_mover(self, msg, mid):
        try:
            v = [float(msg.get(k, 0.0)) for k in ("vx", "vy", "giro")]
        except (TypeError, ValueError):
            return {"tipo": "ack", "id": mid, "ok": False, "erro": "velocidade inválida"}
        if not all(math.isfinite(x) for x in v):
            return {"tipo": "ack", "id": mid, "ok": False, "erro": "velocidade inválida"}
        if self.truque_em_andamento.locked():
            return {"tipo": "ack", "id": mid, "ok": False, "erro": "ocupado"}
        vx, vy, giro, limitado = limitar(*v)
        if limitado:
            log.warning("velocidade pedida %s cortada para %s", v, (vx, vy, giro))
        self._iniciar_movimento(vx, vy, giro)
        return {"tipo": "ack", "id": mid, "ok": True, "acao": "mover",
                "vx": vx, "vy": vy, "giro": giro, "limitado": limitado}

    async def vigia_heartbeat(self):
        # Só age se algum cliente já mandou heartbeat (ações discretas funcionam sem ele).
        while True:
            await asyncio.sleep(0.05)
            if self.ultimo_heartbeat and time.monotonic() - self.ultimo_heartbeat > HEARTBEAT_TIMEOUT_S:
                log.warning("heartbeat perdido -> parar")
                self.ultimo_heartbeat = None
                await self.parar()

    async def conexao(self, ws):
        log.info("cliente conectado: %s", ws.remote_address)
        try:
            async for bruto in ws:
                try:
                    resp = await self.tratar(json.loads(bruto))
                except json.JSONDecodeError:
                    log.warning("mensagem não é JSON: %.80r", bruto)
                    resp = {"tipo": "ack", "ok": False, "erro": "JSON inválido"}
                except Exception as e:  # erro do SDK
                    log.exception("falha")
                    resp = {"tipo": "ack", "ok": False, "erro": str(e)}
                if resp:
                    await ws.send(json.dumps(resp, ensure_ascii=False))
        finally:
            log.info("cliente desconectado -> parar")
            self.ultimo_heartbeat = None
            await self.parar()


async def main():
    import websockets

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
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
