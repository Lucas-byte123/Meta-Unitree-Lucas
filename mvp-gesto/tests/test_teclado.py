"""Testes do teclado.py: os comandos dos testes de parada, contra a ponte em mock."""
import asyncio
import unittest
from unittest import mock

import websockets

import ponte
import teclado


class TestLerSegurar(unittest.TestCase):
    def test_tempo_padrao_e_corte(self):
        self.assertEqual(teclado.ler_segurar("segurar frente 2"), ("frente", 2.0))
        self.assertEqual(teclado.ler_segurar("segurar girar_esq"), ("girar_esq", teclado.SEGURAR_MAX_S))
        self.assertEqual(teclado.ler_segurar("segurar frente 30"), ("frente", teclado.SEGURAR_MAX_S))

    def test_so_movimento_e_tempo_valido(self):
        for linha in ("segurar", "segurar cumprimentar", "segurar frente 0", "segurar frente x",
                      "segurar frente nan"):
            with self.assertRaises(ValueError, msg=linha):
                teclado.ler_segurar(linha)


class TestComPonte(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.robo = ponte.RoboMock()
        self.ponte = ponte.Ponte(self.robo)
        self.vigia = asyncio.create_task(self.ponte.vigia_heartbeat())
        self.servidor = await websockets.serve(self.ponte.conexao, "localhost", 0)
        porta = self.servidor.sockets[0].getsockname()[1]
        self.ws = await websockets.connect(f"ws://localhost:{porta}")
        self.t = teclado.Teclado(self.ws, escrever=lambda texto: None)
        self.fundo = [asyncio.create_task(self.t.heartbeat()), asyncio.create_task(self.t.mostrar_respostas())]

    async def asyncTearDown(self):
        self.t.interromper()
        for tarefa in self.fundo:
            tarefa.cancel()
        await self.ws.close()
        self.servidor.close()
        await self.servidor.wait_closed()
        self.vigia.cancel()

    async def test_teste_heartbeat_para_pelo_vigia_antes_de_expirar(self):
        with mock.patch.object(teclado, "PAUSA_HEARTBEAT_S", 0.6):
            await self.t.tratar_linha("teste_heartbeat")
            # frente em 0 s, heartbeat cortado em 0,3 s, vigia age perto de 0,6 s;
            # o movimento só expiraria em 1 s
            await asyncio.sleep(0.85)
            self.assertIn(("parar",), self.robo.chamadas)
            self.assertFalse(self.ponte.em_movimento())
            await asyncio.sleep(0.3)
            self.assertTrue(self.t.heartbeat_ligado)
            self.assertIsNotNone(self.ponte.ultimo_heartbeat)  # vigia armado de novo

    async def test_segurar_mantem_andando_e_parar_interrompe(self):
        await self.t.tratar_linha("segurar frente 3")
        await asyncio.sleep(1.3)  # um frente sozinho já teria expirado
        self.assertTrue(self.ponte.em_movimento())
        self.assertNotIn(("parar",), self.robo.chamadas)
        self.t.interromper()
        await self.t.tratar_linha("parar")
        await asyncio.sleep(0.6)  # nenhuma renovação chega depois do parar
        self.assertEqual(self.robo.chamadas[-1], ("parar",))
        self.assertFalse(self.ponte.em_movimento())


if __name__ == "__main__":
    unittest.main()
