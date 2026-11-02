# -*- coding: utf-8 -*-
"""Roda os leitores do robô contra as provas REAIS do ano passado e confere com fatos públicos."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'robo'))
import robo as R

ok = True
def check(cond, msg):
    global ok
    print(('  ✅ ' if cond else '  ❌ ') + msg); ok = ok and cond

print('UFPR 2026 (NC-UFPR, caderno com ►)')
u = R.h_nc_ufpr({'base': 'https://servicos.nc.ufpr.br/documentos/ps2026/provas/', 'pagina': 'https://servicos.nc.ufpr.br/PortalNC/Concurso?concurso=PS2026',
                 'alts': 'ABCDE', 'esperado': 90, 'prova_geral': 'INGL'}, {'gab': {}})
check(u.get('status') == 'definitivo', f"status definitivo ({u.get('status')})")
check(len(u.get('gab', {})) >= 82, f"{len(u.get('gab', {}))} questões principais")
check(u.get('gab', {}).get('15') == 'X' and 15 in u.get('anuladas', []), 'Q15 anulada (relatório: 001 Inglês A, Q15)')
check(len(u.get('lem', {})) == 7, f"Língua estrangeira em {len(u.get('lem', {}))} línguas")
check(u.get('gab', {}).get('1') == 'B', 'Q01 (Matemática, livro de R$ 60,00) = B')
check(len(u.get('questoes_auto', [])) >= 80, f"{len(u.get('questoes_auto', []))} enunciados extraídos")

print('ENEM 2025 (Inep)')
e = R.h_inep({'ano': 2025}, {})
vs = e.get('versoes', {})
check(len(vs) >= 8, f'{len(vs)} cadernos lidos: ' + ', '.join(sorted(vs))[:200])
am = next((v for k, v in vs.items() if v['dia'] == 2 and v['caderno'] == 5), None)
check(am is not None and [n for n, x in am['gab'].items() if x == 'X'] == ['115', '121', '178'], 'Dia 2 Amarelo (CD5): anuladas 115, 121, 178')
az = next((v for k, v in vs.items() if v['dia'] == 1 and v['caderno'] == 1), None)
check(az is not None and az['lem']['INGLÊS']['1'] == 'D' and az['lem']['ESPANHOL']['1'] == 'B', 'Dia 1 Azul: Q1 Inglês D / Espanhol B')

print('UFRGS 2026 (Coperse, página HTML)')
g = R.h_ufrgs({'url': 'https://vestibular.ufrgs.br/cv2026/gabaritos/', 'final': '2025-12-05T15:00:00'}, {})
G = g.get('gab', {})
check(g.get('status') == 'definitivo', f"status {g.get('status')}")
check(len(G) == 120, f'{len(G)} questões (75 do 1º dia + 45 do 2º)')
check(G.get('147') == 'X', 'Biologia Q47 anulada (notícia oficial)')
check(G.get('49') == 'A', 'Geografia Q49 alterada D → A (notícia oficial)')
check(G.get('39') == 'B', 'História Q39 alterada D → B (notícia oficial)')
check(len(g.get('lem', {})) == 5 and len(g['lem'].get('INGLÊS', {})) == 15, 'Língua estrangeira: 5 línguas × 15')
print('\nRESULTADO:', 'TODOS OK' if ok else 'FALHAS')
sys.exit(0 if ok else 1)
