# -*- coding: utf-8 -*-
"""Parsers dos gabaritos oficiais.

- caderno_seta(pdf): caderno do NC-UFPR com a alternativa correta marcada por ► (Geral.pdf / 101_cg.pdf).
    Devolve gabarito principal, gabarito de Língua Estrangeira por língua e as questões (enunciado + alternativas).
- inep(pdf): gabarito do ENEM (um PDF por dia/cor de caderno).
- relatorio_ufpr(pdf): relatório de questões anuladas/alteradas do NC-UFPR.
- generico(texto): pares "número → letra" em PDFs/HTML de outras bancas (UFRGS, PUCRS, Vunesp, Coperves).
"""
import re
import unicodedata

LINGUAS = ['ALEMÃO', 'ESPANHOL', 'FRANCÊS', 'INGLÊS', 'ITALIANO', 'JAPONÊS', 'POLONÊS']
MATERIAS = ['MATEMÁTICA', 'FÍSICA', 'QUÍMICA', 'BIOLOGIA', 'GEOGRAFIA', 'HISTÓRIA', 'LÍNGUA PORTUGUESA',
            'LITERATURA BRASILEIRA', 'LITERATURA', 'FILOSOFIA', 'SOCIOLOGIA', 'LÍNGUA ESTRANGEIRA']
# glifos Cambria Math que o NC usa em fórmulas
GLIFOS = {'ൌ': '=', 'െ': '−', '൅': '+', 'ሺ': '(', 'ሻ': ')', 'ି': '⁻', '⋅': '·'}


def pdf_paginas(data):
    import pymupdf
    doc = pymupdf.open(stream=data, filetype='pdf')
    return [p.get_text() for p in doc]


def _limpa(t):
    for a, b in GLIFOS.items():
        t = t.replace(a, b)
    return t


def _norm(s):
    return unicodedata.normalize('NFC', s.strip().upper())


# ---------------------------------------------------------------- NC-UFPR (►)
def caderno_seta(paginas, alts='ABCDE'):
    txt = ''
    for i, p in enumerate(paginas):
        p = re.sub(r'\n\s*\d{1,2}/\d{1,2}\s*\n', '\n', _limpa(p))
        txt += f'\n[[P{i + 1}]]\n' + p
    # cabeçalhos de seção (matéria/língua) em linha própria
    secoes = []
    for m in re.finditer(r'\n[ \t]*([A-ZÁÉÍÓÚÂÊÔÃÕÇ ]{4,30}?)[ \t]*\n', txt):
        nome = _norm(m.group(1))
        if nome in MATERIAS or nome in LINGUAS:
            secoes.append((m.start(), nome))
    ordem = re.search(r'ORDEM\s*\n\s*(?:\n\s*)*([A-Z])\s*\n', txt)
    # blocos de questão: "NN - " no começo da linha, depois do primeiro cabeçalho de seção
    ini = secoes[0][0] if secoes else 0
    heads = [(m.start(), int(m.group(1))) for m in re.finditer(r'\n[ \t]*(\d{1,3})[ \t]*[-–][ \t]', txt) if m.start() >= ini]
    principal, lem, questoes, materia_de = {}, {}, {}, {}
    letras = ''.join(alts)
    for k, (pos, n) in enumerate(heads):
        fim = heads[k + 1][0] if k + 1 < len(heads) else len(txt)
        corpo = txt[pos:fim]
        sec = None
        for sp, nome in secoes:
            if sp <= pos:
                sec = nome
            else:
                break
        setas = re.findall(r'►\s*([%s])\)' % letras, corpo)
        if not re.search(r'(?:^|\n)\s*►?\s*[%s]\)' % letras, corpo):
            continue  # não é questão (ex.: grade de respostas da capa)
        letra = setas[0] if len(setas) == 1 else ('X' if not setas or len(setas) > 1 else None)
        if sec in LINGUAS:
            lem.setdefault(sec, {})[n] = letra
            continue
        if n in principal:
            continue
        principal[n] = letra
        materia_de[n] = sec
        # enunciado + alternativas
        body = re.sub(r'\[\[P\d+\]\]', '', corpo)
        body = re.sub(r'^\s*\d{1,3}\s*[-–]\s*', '', body)
        partes = re.split(r'(?:^|\n)\s*►?\s*([%s])\)\s*' % letras, body)
        enun = re.sub(r'[ \t]*\n[ \t]*', ' ', partes[0]).strip()
        ops = []
        for j in range(1, len(partes) - 1, 2):
            ops.append(re.sub(r'\s+', ' ', partes[j + 1]).strip())
        questoes[n] = {'n': n, 's': sec, 't': enun, 'o': ops, 'oficial': letra}
    return {'ordem': ordem.group(1) if ordem else None, 'gab': principal, 'lem': lem,
            'questoes': [questoes[n] for n in sorted(questoes)], 'materias': materia_de}


def relatorio_ufpr(paginas):
    t = _limpa('\n'.join(paginas))
    anul, alter = [], []
    sec_alt = t.upper().find('ALTERAD', t.upper().find('QUESTÕES ANULADAS') + 20) if 'QUESTÕES ANULADAS' in t.upper() else t.upper().find('ALTERAD')
    for m in re.finditer(r'PROVA:\s*([^\n]+?)\s*\n\s*(?:\n\s*)*QUEST[ÃA]O:\s*(\d+)(.{0,300})', t, re.S):
        prova, n, resto = m.group(1).strip(), int(m.group(2)), m.group(3)
        mm = re.search(r'DE\s*[:\-]?\s*([A-E])\s*PARA\s*[:\-]?\s*([A-E])', resto, re.I)
        if mm:
            alter.append({'prova': prova, 'n': n, 'de': mm.group(1).upper(), 'para': mm.group(2).upper()})
        elif sec_alt != -1 and m.start() > sec_alt and 'ANULADA' not in t[m.start() - 200:m.start()].upper():
            alter.append({'prova': prova, 'n': n})
        else:
            anul.append({'prova': prova, 'n': n})
    return {'anuladas': anul, 'alteradas': alter}


# ---------------------------------------------------------------- ENEM / Inep
CORES = ['AZUL', 'AMARELO', 'BRANCO', 'ROSA', 'CINZA', 'VERDE', 'LARANJA', 'ROXO']


def inep(paginas):
    t = '\n'.join(paginas)
    toks = [x.strip() for x in t.split('\n') if x.strip()]
    cor = next((c.capitalize() for c in CORES if re.search(r'\b%s\b' % c, t.upper())), None)
    cad = re.search(r'CADERNO\s*(\d+)', t.upper())
    gab, lem = {}, {'INGLÊS': {}, 'ESPANHOL': {}}
    i = 0
    while i < len(toks):
        if re.fullmatch(r'\d{1,3}', toks[i]):
            n = int(toks[i])
            a = toks[i + 1] if i + 1 < len(toks) else ''
            b = toks[i + 2] if i + 2 < len(toks) else ''
            val = lambda x: 'X' if x.upper().startswith('ANULAD') else (x.upper() if re.fullmatch(r'[A-Ea-e]', x) else None)
            va, vb = val(a), val(b)
            if va and 1 <= n <= 5 and vb and n not in gab:
                lem['INGLÊS'][n] = va; lem['ESPANHOL'][n] = vb; i += 3; continue
            if va and 1 <= n <= 180:
                gab.setdefault(n, va); i += 2; continue
        i += 1
    d = (1 if min(gab) <= 90 else 2) if gab else None  # a numeração define o dia (1–90 / 91–180)
    return {'cor': cor, 'caderno': int(cad.group(1)) if cad else None, 'dia': d, 'gab': gab,
            'lem': {k: v for k, v in lem.items() if v}}


# ---------------------------------------------------------------- genérico
def generico(texto, n_min=1, n_max=200, alts='ABCDE'):
    """Procura pares número→letra. Aceita '01 B', '01 - B', '01) B', '01. B', tabelas em colunas e 'ANULADA'."""
    t = _limpa(texto)
    pares = {}
    for m in re.finditer(r'(?<![\d,.])(\d{1,3})\s*[-–).:]?\s+(ANULADA|ANULADO|\*|[%s])(?![A-Za-zÀ-ú])' % alts, t, re.I):
        n = int(m.group(1)); v = m.group(2).upper()
        if n_min <= n <= n_max and n not in pares:
            pares[n] = 'X' if v.startswith('ANUL') or v == '*' else v
    # formato em colunas (um token por linha), como no Inep
    toks = [x.strip() for x in t.split('\n') if x.strip()]
    for i in range(len(toks) - 1):
        if re.fullmatch(r'\d{1,3}', toks[i]) and re.fullmatch(r'[%s]|ANULAD[AO]' % alts, toks[i + 1], re.I):
            n = int(toks[i])
            if n_min <= n <= n_max:
                pares.setdefault(n, 'X' if toks[i + 1].upper().startswith('ANUL') else toks[i + 1].upper())
    # aceita só uma sequência coerente (cobre ≥ 60% de um intervalo contínuo)
    if not pares:
        return {}
    ns = sorted(pares)
    cobertura = len(ns) / (ns[-1] - ns[0] + 1)
    return pares if (len(ns) >= 10 and cobertura >= 0.6) else {}
