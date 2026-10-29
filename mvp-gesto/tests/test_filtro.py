import unittest

from filtro import FiltroGesto

MAPA = {"Thumb_Up": "cumprimentar", "Victory": "sentar", "Open_Palm": "parar"}


def rodar(filtro, quadros):
    """quadros: lista de (t_ms, gesto, confiança). Devolve [(t_ms, ação)] disparadas."""
    saida = []
    for t, g, c in quadros:
        acao = filtro.atualizar(g, c, t)
        if acao:
            saida.append((t, acao))
    return saida


def segurar(gesto, de, ate, passo=33, conf=0.9):
    return [(t, gesto, conf) for t in range(de, ate, passo)]


class TestFiltroGesto(unittest.TestCase):
    def test_dispara_depois_de_estavel(self):
        f = FiltroGesto(MAPA)
        disparos = rodar(f, segurar("Thumb_Up", 0, 1000))
        self.assertEqual(len(disparos), 1)
        t, acao = disparos[0]
        self.assertEqual(acao, "cumprimentar")
        self.assertGreaterEqual(t, 500)
        self.assertLess(t, 550)

    def test_nao_dispara_antes_do_tempo(self):
        f = FiltroGesto(MAPA)
        self.assertEqual(rodar(f, segurar("Thumb_Up", 0, 450)), [])

    def test_confianca_baixa_nao_conta(self):
        f = FiltroGesto(MAPA)
        self.assertEqual(rodar(f, segurar("Thumb_Up", 0, 2000, conf=0.5)), [])

    def test_nao_repete_sem_baixar_a_mao(self):
        f = FiltroGesto(MAPA)
        disparos = rodar(f, segurar("Thumb_Up", 0, 3000))
        self.assertEqual(len(disparos), 1)

    def test_repete_depois_de_baixar_a_mao(self):
        f = FiltroGesto(MAPA)
        quadros = segurar("Thumb_Up", 0, 1000) + segurar(None, 1000, 1200) + segurar("Thumb_Up", 1200, 2200)
        self.assertEqual([a for _, a in rodar(f, quadros)], ["cumprimentar", "cumprimentar"])

    def test_tremida_reinicia_a_contagem(self):
        f = FiltroGesto(MAPA)
        quadros = segurar("Thumb_Up", 0, 400) + [(400, "Victory", 0.9)] + segurar("Thumb_Up", 433, 800)
        self.assertEqual(rodar(f, quadros), [])

    def test_parar_e_mais_rapido(self):
        f = FiltroGesto(MAPA)
        disparos = rodar(f, segurar("Open_Palm", 0, 400))
        self.assertEqual(len(disparos), 1)
        t, acao = disparos[0]
        self.assertEqual(acao, "parar")
        self.assertLess(t, 250)

    def test_parar_aceita_confianca_mais_baixa(self):
        # 0,6: abaixo do mínimo dos truques (0,65), acima do do parar (0,55)
        self.assertEqual([a for _, a in rodar(FiltroGesto(MAPA), segurar("Open_Palm", 0, 400, conf=0.6))], ["parar"])
        self.assertEqual(rodar(FiltroGesto(MAPA), segurar("Thumb_Up", 0, 2000, conf=0.6)), [])

    def test_parar_abaixo_do_minimo_nao_dispara(self):
        self.assertEqual(rodar(FiltroGesto(MAPA), segurar("Open_Palm", 0, 2000, conf=0.5)), [])

    def test_gesto_fora_do_mapa_nao_dispara(self):
        f = FiltroGesto(MAPA)
        self.assertEqual(rodar(f, segurar("ILoveYou", 0, 2000)), [])

    def test_trocar_de_gesto_dispara_o_novo(self):
        f = FiltroGesto(MAPA)
        quadros = segurar("Thumb_Up", 0, 800) + segurar("Victory", 800, 1600)
        self.assertEqual([a for _, a in rodar(f, quadros)], ["cumprimentar", "sentar"])

    def test_progresso(self):
        f = FiltroGesto(MAPA)
        f.atualizar("Thumb_Up", 0.9, 0)
        self.assertAlmostEqual(f.progresso(250), 0.5)
        f.atualizar("Thumb_Up", 0.9, 600)
        self.assertEqual(f.progresso(600), 0.0)  # já disparou


if __name__ == "__main__":
    unittest.main()
