"""Filtro anti-disparo: transforma o gesto reconhecido em cada frame numa ação.

Sem dependências, para rodar igual na webcam, em vídeo gravado e nos testes.
O app Android deve reproduzir esta mesma lógica.

Regras:
- confiança abaixo do mínimo conta como "sem gesto"; o mínimo do "parar" é mais
  baixo, porque um parar à toa só para o robô e um parar perdido é perigoso;
- o gesto precisa ficar estável por um tempo antes de valer (parar é mais rápido);
- depois de disparar, o mesmo gesto só vale de novo depois de baixar a mão
  (ou trocar de gesto).
"""

# Medido em 28/10/2026 no celular (app-android): Thumb_Up e Open_Palm ficam
# entre 0,6 e 0,7, então 0,7 quase nunca disparava.
CONFIANCA_MIN = 0.65
CONFIANCA_MIN_PARAR = 0.55
ESTAVEL_MS = 500         # gesto parado por ~0,5 s antes de valer
ESTAVEL_PARAR_MS = 200   # "parar" tem prioridade: vale mais rápido


class FiltroGesto:
    def __init__(self, mapa, confianca_min=CONFIANCA_MIN, confianca_min_parar=CONFIANCA_MIN_PARAR,
                 estavel_ms=ESTAVEL_MS, estavel_parar_ms=ESTAVEL_PARAR_MS):
        self.mapa = mapa
        self.confianca_min = confianca_min
        self.confianca_min_parar = confianca_min_parar
        self.estavel_ms = estavel_ms
        self.estavel_parar_ms = estavel_parar_ms
        self.atual = None       # gesto visto agora (já filtrado pela confiança)
        self.desde_ms = None    # desde quando o gesto atual está estável
        self.disparado = None   # último gesto que virou ação

    def atualizar(self, gesto, confianca, t_ms):
        """Recebe o gesto de um frame e devolve a ação a disparar, ou None."""
        g = gesto if self.vale(gesto, confianca) else None
        if g != self.atual:
            self.atual, self.desde_ms = g, t_ms
        if g is None:
            self.disparado = None  # mão baixou: o próximo gesto pode disparar
            return None
        if g not in self.mapa or g == self.disparado:
            return None
        acao = self.mapa[g]
        espera = self.estavel_parar_ms if acao == "parar" else self.estavel_ms
        if t_ms - self.desde_ms >= espera:
            self.disparado = g
            return acao
        return None

    def vale(self, gesto, confianca):
        """Se o gesto passa da confiança mínima (a do parar é mais baixa)."""
        if gesto is None:
            return False
        minimo = self.confianca_min_parar if self.mapa.get(gesto) == "parar" else self.confianca_min
        return confianca >= minimo

    def progresso(self, t_ms):
        """Fração (0 a 1) do tempo de estabilidade já cumprido pelo gesto atual."""
        if self.atual not in self.mapa or self.atual == self.disparado:
            return 0.0
        espera = self.estavel_parar_ms if self.mapa[self.atual] == "parar" else self.estavel_ms
        return min(1.0, (t_ms - self.desde_ms) / espera)
