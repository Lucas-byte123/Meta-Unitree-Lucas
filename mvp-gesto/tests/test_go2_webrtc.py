import asyncio
import json
import sys
import types
import unittest
from unittest import mock

import ponte
from ponte import Ponte, RoboGo2WebRTC
from tests.test_ponte import TEMPOS

# Imitação da unitree_webrtc_connect 2.2.0: só o que o backend usa.
# Os números são os de SPORT_CMD e RTC_TOPIC da biblioteca.
SPORT_CMD = {"Damp": 1001, "StopMove": 1003, "Move": 1008, "Sit": 1009, "RiseSit": 1010,
             "Hello": 1016, "Stretch": 1017}
TOPICO = "rt/api/sport/request"
TOPICO_MODO = "rt/api/motion_switcher/request"
OK = {"data": {"header": {"status": {"code": 0}}}}


class ConexaoFalsa:
    """Grava os pedidos; `resposta`, `travar` e `estado` simulam o robô."""
    ultima = None

    def __init__(self, metodo, ip=None, aes_128_key=None, **_):
        self.metodo, self.ip, self.chave = metodo, ip, aes_128_key
        self.pedidos = []
        self.sem_resposta = []  # Move: publish_without_callback
        self.resposta = OK
        self.travar = False
        self.estado = "connected"
        self.pc = None
        self.datachannel = types.SimpleNamespace(pub_sub=types.SimpleNamespace(
            publish_request_new=self._publicar, publish_without_callback=self._publicar_sem_resposta))
        ConexaoFalsa.ultima = self

    async def disconnect(self):
        self.pc = None

    async def connect(self):
        self.pc = types.SimpleNamespace(connectionState=self.estado)

    def _publicar_sem_resposta(self, topico, carga):
        asyncio.get_running_loop()  # falha se chamado fora do loop do WebRTC
        self.sem_resposta.append((topico, carga))

    async def _publicar(self, topico, opcoes):
        self.pedidos.append((topico, opcoes))
        if self.travar:
            await asyncio.sleep(3600)  # a biblioteca espera a resposta sem prazo
        return self.resposta


def biblioteca_falsa():
    m = types.ModuleType("unitree_webrtc_connect")
    m.UnitreeWebRTCConnection = ConexaoFalsa
    m.WebRTCConnectionMethod = types.SimpleNamespace(LocalAP=1, LocalSTA=2, Remote=3)
    m.RTC_TOPIC = {"SPORT_MOD": TOPICO, "MOTION_SWITCHER": TOPICO_MODO}
    m.SPORT_CMD = SPORT_CMD
    return m


class TestRoboGo2WebRTC(unittest.TestCase):
    def setUp(self):
        p = mock.patch.dict(sys.modules, {"unitree_webrtc_connect": biblioteca_falsa()})
        p.start()
        self.addCleanup(p.stop)
        self.robo = RoboGo2WebRTC("192.168.0.50", "chave", "sta")
        self.conn = ConexaoFalsa.ultima

    def api_ids(self):
        return [o["api_id"] for _, o in self.conn.pedidos]

    def test_conecta_com_ip_e_chave(self):
        self.assertEqual((self.conn.metodo, self.conn.ip, self.conn.chave), (2, "192.168.0.50", "chave"))

    def test_truques_viram_comandos_do_sdk(self):
        for acao, nome in [("cumprimentar", "Hello"), ("sentar", "Sit"), ("levantar", "RiseSit"), ("alongar", "Stretch")]:
            self.robo.executar(acao)
            self.assertEqual(self.conn.pedidos[-1], (TOPICO, {"api_id": SPORT_CMD[nome]}))

    def test_nunca_damp(self):
        self.assertNotIn("Damp", self.robo.acoes.values())
        self.assertNotIn(SPORT_CMD["Damp"], self.api_ids())

    def test_mover_vai_sem_esperar_resposta(self):
        self.conn.travar = True  # se o Move esperasse resposta, travaria aqui
        self.robo.mover(0.2, 0.0, -0.5)
        topico, carga = self.conn.sem_resposta[-1]
        self.assertEqual(topico, TOPICO)
        self.assertEqual(carga["header"]["identity"]["api_id"], SPORT_CMD["Move"])
        self.assertTrue(carga["header"]["policy"]["noreply"])
        self.assertEqual(json.loads(carga["parameter"]), {"x": 0.2, "y": 0.0, "z": -0.5})
        self.assertEqual(self.conn.pedidos, [])

    def test_parar_espera_resposta(self):
        self.robo.parar()
        self.assertEqual(self.conn.pedidos, [(TOPICO, {"api_id": SPORT_CMD["StopMove"]})])

    def test_robo_que_nao_responde_estoura_o_prazo(self):
        self.conn.travar = True
        with mock.patch.object(RoboGo2WebRTC, "PRAZO_S", 0.1):
            with self.assertRaises(Exception):
                self.robo.parar()

    def test_conexao_caida_e_erro(self):
        self.conn.pc.connectionState = "failed"
        with self.assertRaises(ConnectionError):
            self.robo.mover(0.1, 0, 0)
        self.assertEqual((self.conn.pedidos, self.conn.sem_resposta), ([], []))

    def test_codigo_de_erro_do_robo_e_erro(self):
        self.conn.resposta = {"data": {"header": {"status": {"code": 3203}}}}
        with self.assertRaises(RuntimeError):
            self.robo.executar("sentar")


class TestChecarGo2(unittest.TestCase):
    """checar_go2.py: conecta e lê o modo, sem nenhum comando de movimento."""

    def setUp(self):
        p = mock.patch.dict(sys.modules, {"unitree_webrtc_connect": biblioteca_falsa()})
        p.start()
        self.addCleanup(p.stop)
        self.robo = RoboGo2WebRTC("192.168.0.50")
        self.conn = ConexaoFalsa.ultima

    def test_le_o_modo_sem_mover(self):
        import checar_go2
        self.conn.resposta = {"data": {"header": {"status": {"code": 0}}, "data": json.dumps({"name": "normal"})}}
        self.assertEqual(checar_go2.ler_modo(self.robo), "normal")
        self.assertEqual(self.conn.pedidos, [(TOPICO_MODO, {"api_id": 1001})])  # só a leitura
        self.assertEqual(self.conn.sem_resposta, [])  # nenhum Move


class TestPonteComGo2WebRTC(unittest.IsolatedAsyncioTestCase):
    """A ponte inteira com o backend WebRTC (e a biblioteca falsa)."""

    def setUp(self):
        self.patches = [mock.patch.dict(sys.modules, {"unitree_webrtc_connect": biblioteca_falsa()})]
        self.patches += [mock.patch.object(ponte, k, v) for k, v in TEMPOS.items()]
        for p in self.patches:
            p.start()
        self.robo = RoboGo2WebRTC("192.168.0.50")
        self.conn = ConexaoFalsa.ultima
        self.ponte = Ponte(self.robo)

    def tearDown(self):
        for p in self.patches:
            p.stop()

    async def test_movimento_expira_com_stopmove(self):
        await self.ponte.tratar({"tipo": "acao", "acao": "frente"})
        await asyncio.sleep(0.45)  # DURACAO_MOVIMENTO_S = 0,3 nos testes
        self.assertGreaterEqual(len(self.conn.sem_resposta), 2)  # Move reenviado
        self.assertEqual(self.conn.pedidos[-1], (TOPICO, {"api_id": SPORT_CMD["StopMove"]}))

    async def test_conexao_caida_no_meio_do_movimento_nao_trava_a_ponte(self):
        await self.ponte.tratar({"tipo": "acao", "acao": "frente"})
        await asyncio.sleep(0.1)
        self.conn.pc.connectionState = "failed"
        await asyncio.sleep(0.2)
        self.assertFalse(self.ponte.em_movimento())  # a tarefa não ficou presa nem morreu calada


if __name__ == "__main__":
    unittest.main()
