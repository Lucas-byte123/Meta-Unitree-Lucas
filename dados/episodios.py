"""Resume um CSV do app em trechos com a mão visível: gestos, confiança e ações.

Uso: python3 dados/episodios.py dados/gestos-AAAAMMDD-HHMMSS.csv
"""
import csv, sys
from collections import Counter, defaultdict
linhas = list(csv.DictReader(open(sys.argv[1])))
t0 = int(linhas[0]["t_ms"])
# acao -> relógio: primeira ação do CSV
for l in linhas:
    if l["acao"]:
        print("primeira ação em t=%.1f s (%s)" % ((int(l["t_ms"]) - t0) / 1000, l["acao"])); break
ant = None
for l in linhas:
    t = int(l["t_ms"])
    if ant and t - ant > 300:
        print("  [buraco de %d ms sem frames em t=%.1f s]" % (t - ant, (ant - t0) / 1000))
    ant = t
# episódios: trechos com mão, juntando falhas de até 1 s
eps, atual, ult_mao = [], [], None
for l in linhas:
    t = int(l["t_ms"])
    if l["tem_mao"] == "1":
        if ult_mao is not None and t - ult_mao > 1000 and atual:
            eps.append(atual); atual = []
        atual.append(l); ult_mao = t
if atual: eps.append(atual)
for e in eps:
    ti, tf = (int(e[0]["t_ms"]) - t0) / 1000, (int(e[-1]["t_ms"]) - t0) / 1000
    if tf - ti < 0.5: continue
    g = defaultdict(list)
    for l in e: g[l["gesto"] or "(nenhum)"].append(float(l["confianca"]))
    resumo = ", ".join("%s %d q (média %.2f, máx %.2f, >=0,7: %d)" % (k, len(v), sum(v)/len(v), max(v), sum(c >= 0.7 for c in v))
                       for k, v in sorted(g.items(), key=lambda kv: -len(kv[1])) if len(v) >= 3)
    acoes = [l["acao"] for l in e if l["acao"]]
    print("%6.1f-%6.1f s (%4.1f s, %3d quadros) %s | ações: %s" % (ti, tf, tf - ti, len(e), resumo, acoes or "-"))
