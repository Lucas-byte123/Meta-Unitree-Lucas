import asyncio
import json
import unittest
from unittest import mock

import ponte
from ponte import Ponte, RoboMock

# tempos curtos para os testes rodarem rápido
TEMPOS = {
    "DURACAO_MOVIMENTO_S": 0.3,
    "REENVIO_MOVIMENTO_S": 0.05,
    "HEARTBEAT_TIMEOUT_S": 0.15,
    "COOLDOWN_S": 0.3,
}


class FakeWS:
    """Imita a conexão do websockets: entrega mensagens e guarda as respostas."""
    remote_address = ("teste", 0)

    def __init__(self, mensagens, intervalo=0.0):
        self.mensagens = mensagens
        self.intervalo = intervalo
        self.enviadas = []

    def __aiter__(self):
        return self._gerar()

    async def _gerar(self):
        for m in self.mensagens:
            await asyncio.sleep(self.intervalo)
            yield json.dumps(m)

    async def send(self, texto):
        self.enviadas.append(json.loads(texto))


class TestPonte(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.patches = [mock.patch.object(ponte, k, v) for k, v in TEMPOS.items()]
        for p in self.patches:
            p.start()
        self.robo = RoboMock()
        self.ponte = Ponte(self.robo)

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def nomes(self):
        return [c[0] for c in self.robo.chamadas]

    async def acao(self, acao):
        return await self.ponte.tratar({"tipo": "acao", "acao": acao, "id": "x"})

    # truques

    async def test_truque_executa(self):
        r = await self.acao("cumprimentar")
        self.assertTrue(r["ok"])
        self.assertEqual(self.robo.chamadas, [("executar", "cumprimentar")])

    async def test_acao_fora_da_lista_e_recusada(self):
        r = await self.acao("dar_cambalhota")
        self.assertFalse(r["ok"])
        self.assertIn("não permitida", r["erro"])
        self.assertEqual(self.robo.chamadas, [])

    async def test_cooldown_entre_truques(self):
        await self.acao("cumprimentar")
        r = await self.acao("sentar")
        self.assertFalse(r["ok"])
        self.assertEqual(r["erro"], "ocupado")
        await asyncio.sleep(0.35)
        self.assertTrue((await self.acao("sentar"))["ok"])

    async def test_truque_recusado_com_robo_andando(self):
        await self.acao("frente")
        r = await self.acao("cumprimentar")
        self.assertFalse(r["ok"])
        self.assertEqual(r["erro"], "em movimento")
        await self.ponte.parar()

    async def test_tipo_desconhecido(self):
        r = await self.ponte.tratar({"tipo": "dancar"})
        self.assertFalse(r["ok"])

    # movimento

    async def test_movimento_expira_sozinho(self):
        r = await self.acao("frente")
        self.assertTrue(r["ok"])
        await asyncio.sleep(0.1)
        self.assertIn(("mover", 0.2, 0.0, 0.0), self.robo.chamadas)
        await asyncio.sleep(0.4)
        self.assertEqual(self.robo.chamadas[-1], ("parar",))
        self.assertFalse(self.ponte.em_movimento())

    async def test_movimento_reenvia_enquanto_vale(self):
        await self.acao("frente")
        await asyncio.sleep(0.25)
        self.assertGreaterEqual(self.nomes().count("mover"), 3)
        await self.ponte.parar()

    async def test_renovar_nao_para_no_meio(self):
        await self.acao("frente")
        await asyncio.sleep(0.2)
        await self.acao("frente")
        await asyncio.sleep(0.2)
        self.assertNotIn("parar", self.nomes())  # 0,4 s andando sem parar
        await asyncio.sleep(0.3)
        self.assertEqual(self.robo.chamadas[-1], ("parar",))

    async def test_parar_interrompe_movimento(self):
        await self.acao("girar_esq")
        await asyncio.sleep(0.1)
        r = await self.acao("parar")
        self.assertTrue(r["ok"])
        n = len(self.robo.chamadas)
        self.assertEqual(self.robo.chamadas[-1], ("parar",))
        await asyncio.sleep(0.2)
        self.assertEqual(len(self.robo.chamadas), n)  # nenhum mover depois do parar

    async def test_parar_sempre_chega_por_ultimo(self):
        # mover lento no "SDK": o parar não pode passar na frente de um mover em andamento
        lento = self.robo.mover

        def mover_lento(*a):
            import time
            time.sleep(0.05)
            lento(*a)

        self.robo.mover = mover_lento
        await self.acao("frente")
        await asyncio.sleep(0.02)  # no meio do primeiro mover
        await self.acao("parar")
        await asyncio.sleep(0.15)
        self.assertEqual(self.robo.chamadas[-1], ("parar",))

    async def test_falha_ao_mover_manda_parar(self):
        # robô que recusa o Move (ex.: WebRTC instável): a ponte não pode só desistir em silêncio
        def mover_que_falha(*a):
            raise RuntimeError("robô recusou Move")

        self.robo.mover = mover_que_falha
        await self.acao("frente")
        await asyncio.sleep(0.1)
        self.assertEqual(self.robo.chamadas[-1], ("parar",))
        self.assertFalse(self.ponte.em_movimento())

    async def test_vigia_sobrevive_a_falha_ao_parar(self):
        def parar_que_falha():
            raise ConnectionError("sem conexão com o robô")

        self.robo.parar = parar_que_falha
        vigia = asyncio.create_task(self.ponte.vigia_heartbeat())
        try:
            await self.ponte.tratar({"tipo": "heartbeat"})
            await asyncio.sleep(0.25)  # heartbeat perdido -> parar falha
            self.assertFalse(vigia.done())  # o vigia continua de pé
        finally:
            vigia.cancel()

    async def test_mover_acima_do_limite_e_cortado(self):
        r = await self.ponte.tratar({"tipo": "mover", "vx": 2.0, "vy": -1.0, "giro": 5.0})
        self.assertTrue(r["ok"])
        self.assertTrue(r["limitado"])
        self.assertEqual((r["vx"], r["vy"], r["giro"]),
                         (ponte.VEL_MAX_LINEAR, -ponte.VEL_MAX_LINEAR, ponte.VEL_MAX_GIRO))
        await asyncio.sleep(0.05)
        self.assertIn(("mover", 0.3, -0.3, 0.6), self.robo.chamadas)
        await self.ponte.parar()

    async def test_mover_dentro_do_limite(self):
        r = await self.ponte.tratar({"tipo": "mover", "vx": 0.1})
        self.assertFalse(r["limitado"])
        self.assertEqual((r["vx"], r["vy"], r["giro"]), (0.1, 0.0, 0.0))
        await self.ponte.parar()

    async def test_mover_invalido_e_recusado(self):
        for msg in ({"vx": "rápido"}, {"vx": float("nan")}, {"giro": float("inf")}, {"vx": None}):
            r = await self.ponte.tratar({"tipo": "mover", **msg})
            self.assertFalse(r["ok"], msg)
        self.assertEqual(self.robo.chamadas, [])

    # heartbeat e conexão

    async def test_heartbeat_perdido_para_o_robo(self):
        vigia = asyncio.create_task(self.ponte.vigia_heartbeat())
        try:
            await self.ponte.tratar({"tipo": "heartbeat"})
            await self.ponte.tratar({"tipo": "mover", "vx": 0.1})
            await asyncio.sleep(0.25)  # sem heartbeat por mais de 0,15 s
            self.assertEqual(self.robo.chamadas[-1], ("parar",))
            self.assertFalse(self.ponte.em_movimento())
        finally:
            vigia.cancel()

    async def test_heartbeat_em_dia_nao_para(self):
        vigia = asyncio.create_task(self.ponte.vigia_heartbeat())
        try:
            for _ in range(5):
                await self.ponte.tratar({"tipo": "heartbeat"})
                await asyncio.sleep(0.05)
            self.assertNotIn("parar", self.nomes())
        finally:
            vigia.cancel()

    async def test_desconexao_para_o_robo(self):
        ws = FakeWS([{"tipo": "acao", "acao": "frente", "id": "a"}])
        await self.ponte.conexao(ws)
        self.assertEqual(ws.enviadas[0]["ok"], True)
        self.assertEqual(self.robo.chamadas[-1], ("parar",))
        self.assertFalse(self.ponte.em_movimento())

    async def test_json_invalido_responde_erro(self):
        class WSQuebrado(FakeWS):
            async def _gerar(self):
                yield "isto não é json"

        ws = WSQuebrado([])
        await self.ponte.conexao(ws)
        self.assertFalse(ws.enviadas[0]["ok"])


if __name__ == "__main__":
    unittest.main()
