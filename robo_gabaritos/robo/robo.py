# -*- coding: utf-8 -*-
"""Robô de gabaritos 2027 — roda no GitHub Actions a cada 15 min e publica docs/gabaritos.json.

O app (Missão Medicina) baixa esse JSON ao abrir e a cada 10 min, preenche o gabarito oficial,
corrige o cartão-resposta do aluno e mostra as notícias de correções extraoficiais.

Uso local:  python robo/robo.py [--saida docs/gabaritos.json] [--so ufpr27] [--forcar]
"""
import argparse, datetime as dt, hashlib, html, json, os, re, sys, time, warnings
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, quote_plus

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parsers as P

warnings.filterwarnings('ignore')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36 robo-gabaritos'}
BRT = dt.timezone(dt.timedelta(hours=-3))
CFG = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json'), encoding='utf-8'))


def agora():
    return dt.datetime.now(BRT)


def get(url, timeout=40):
    """GET tolerante: tenta com verificação TLS e cai para sem verificação (sites gov.br têm cadeia incompleta)."""
    for verify in (True, False):
        try:
            r = requests.get(url, headers=UA, timeout=timeout, verify=verify, allow_redirects=True)
            return r
        except requests.exceptions.SSLError:
            continue
        except Exception as ex:  # noqa
            return None
    return None


def texto(r):
    try:
        return r.content.decode('utf-8')
    except UnicodeDecodeError:
        return r.content.decode(r.encoding or 'latin-1', errors='replace')


def get_pdf(url):
    r = get(url)
    if r is not None and r.status_code == 200 and r.content[:5] == b'%PDF-':
        return r.content
    return None


def links_da_pagina(url, palavras):
    r = get(url)
    if r is None or r.status_code != 200:
        return [], (r.status_code if r is not None else 'erro de rede')
    out = []
    for m in re.finditer(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', texto(r), re.S | re.I):
        href, txt = m.group(1), html.unescape(re.sub(r'<[^>]+>', ' ', m.group(2)))
        txt = re.sub(r'\s+', ' ', txt).strip()
        alvo = (href + ' ' + txt).lower()
        if any(p in alvo for p in palavras):
            out.append({'url': urljoin(r.url, href), 'titulo': txt[:160]})
    vistos, uniq = set(), []
    for l in out:
        if l['url'] not in vistos:
            vistos.add(l['url']); uniq.append(l)
    return uniq, 200


def noticias(consulta, desde, exigir=None):
    """Google Notícias (RSS): correções extraoficiais publicadas por cursinhos e portais."""
    url = 'https://news.google.com/rss/search?q=%s&hl=pt-BR&gl=BR&ceid=BR:pt-419' % quote_plus(consulta)
    r = get(url, 30)
    if r is None or r.status_code != 200:
        return []
    out = []
    try:
        root = ET.fromstring(r.content)
        for it in root.iter('item'):
            t = (it.findtext('title') or '').strip()
            link = (it.findtext('link') or '').strip()
            pub = it.findtext('pubDate') or ''
            fonte = (it.find('source').text if it.find('source') is not None else '') or ''
            try:
                quando = dt.datetime.strptime(pub[:25], '%a, %d %b %Y %H:%M:%S').replace(tzinfo=dt.timezone.utc).astimezone(BRT)
            except Exception:
                quando = None
            if quando and quando.date() < desde:
                continue
            if exigir and not any(x.lower() in t.lower() for x in exigir):
                continue
            out.append({'titulo': t[:200], 'url': link, 'fonte': fonte, 'quando': quando.isoformat(timespec='minutes') if quando else ''})
    except ET.ParseError:
        pass
    return out[:12]


# ------------------------------------------------------------------ handlers
def h_nc_ufpr(c, ant):
    res = {'fontes': [], 'log': []}
    base = c['base']
    escolhido = None
    for status, rel in (('definitivo', 'definitivo/Geral.pdf'), ('preliminar', 'provisorio/Geral.pdf')):
        pdf = get_pdf(base + rel)
        if pdf:
            escolhido = (status, base + rel, pdf)
            break
        res['log'].append(f'{rel}: ainda não publicado')
    # descobre links novos na página do concurso (se o NC mudar o nome do arquivo)
    links, st = links_da_pagina(c['pagina'], ['gabarito', '/provas/'])
    res['links'] = [dict(l, nome='NC-UFPR') for l in links]
    if not escolhido:
        for l in links:
            if l['url'].lower().endswith('.pdf') and 'gabarito' in (l['titulo'] + l['url']).lower():
                pdf = get_pdf(l['url'])
                if pdf:
                    escolhido = ('definitivo' if 'definitiv' in (l['titulo'] + l['url']).lower() else 'preliminar', l['url'], pdf)
                    break
    if not escolhido:
        return res
    status, url, pdf = escolhido
    r = P.caderno_seta(P.pdf_paginas(pdf), c.get('alts', 'ABCD'))
    gab = {str(n): v for n, v in r['gab'].items()}
    lem = {lg: {str(n): v for n, v in d.items()} for lg, d in r['lem'].items()}
    anul, alter = [int(n) for n, v in gab.items() if v == 'X'], []
    if status == 'definitivo':
        rel = get_pdf(base + 'definitivo/relatorio-anuladas-alteradas.pdf')
        if rel:
            rr = P.relatorio_ufpr(P.pdf_paginas(rel))
            alvo = c.get('prova_geral', 'INGL')
            for a in rr['anuladas']:
                if alvo in a['prova'].upper() and not a['prova'].strip().upper().endswith(' B'):
                    anul.append(a['n']); gab[str(a['n'])] = 'X'
            alter = [a for a in rr['alteradas'] if alvo in a['prova'].upper() and not a['prova'].strip().upper().endswith(' B')]
            res['fontes'].append({'tipo': 'oficial', 'nome': 'Relatório de anuladas/alteradas (NC-UFPR)', 'url': base + 'definitivo/relatorio-anuladas-alteradas.pdf'})
        # questões que sumiram do definitivo e existiam no preliminar = anuladas
        prev = (ant or {}).get('gab', {})
        for n in prev:
            if n not in gab:
                gab[n] = 'X'; anul.append(int(n))
    esperado = c.get('esperado')
    total = len([v for v in gab.values()]) + len(next(iter(lem.values()), {}))
    if esperado and total < esperado * 0.85:
        res['log'].append(f'leitura parcial ({total}/{esperado}) — conferir PDF manualmente')
    res.update({'status': status, 'gab': gab, 'lem': lem, 'anuladas': sorted(set(anul)), 'alteradas': alter,
                'ordem': r['ordem'], 'materias': {str(n): s for n, s in r['materias'].items()},
                'questoes_auto': r['questoes']})
    res['fontes'].insert(0, {'tipo': 'oficial', 'nome': f'Caderno com gabarito {status} (NC-UFPR, ordem {r["ordem"] or "?"})', 'url': url})
    return res


def h_inep(c, ant):
    res = {'fontes': [], 'log': [], 'versoes': {}}
    ano = c['ano']
    for dia in (1, 2):
        for cd in range(1, 15):
            url = f'https://download.inep.gov.br/enem/provas_e_gabaritos/{ano}_GB_impresso_D{dia}_CD{cd}.pdf'
            pdf = get_pdf(url)
            if not pdf:
                continue
            g = P.inep(P.pdf_paginas(pdf))
            if not g['gab']:
                res['log'].append(f'D{dia} CD{cd}: PDF sem gabarito legível'); continue
            nome = f'Dia {g["dia"] or dia} · {g["cor"] or "Caderno " + str(cd)} (caderno {cd})'
            res['versoes'][nome] = {'dia': g['dia'] or dia, 'cor': g['cor'], 'caderno': cd,
                                    'gab': {str(n): v for n, v in g['gab'].items()},
                                    'lem': {lg: {str(n): v for n, v in d.items()} for lg, d in g['lem'].items()}}
            res['fontes'].append({'tipo': 'oficial', 'nome': f'Inep · {nome}', 'url': url})
    if res['versoes']:
        res['status'] = 'oficial'
    else:
        res['log'].append('gabaritos do Inep ainda não publicados')
    return res


def h_ufrgs(c, ant):
    res = {'fontes': [], 'log': []}
    r = get(c['url'])
    if r is None or r.status_code != 200 or 'Gabaritos' not in texto(r):
        res['log'].append(f'página de gabaritos ainda não publicada ({r.status_code if r is not None else "erro"})')
        return res
    t = re.sub(r'<script.*?</script>|<style.*?</style>', '', texto(r), flags=re.S)
    t = html.unescape(re.sub(r'<[^>]+>', '\n', t))
    toks = [x.strip() for x in t.split('\n') if x.strip()]
    DIA1 = ['LÍNGUA PORTUGUESA', 'LITERATURA EM LÍNGUA PORTUGUESA', 'HISTÓRIA', 'GEOGRAFIA', 'MATEMÁTICA']
    DIA2 = ['FÍSICA', 'QUÍMICA', 'BIOLOGIA']
    gab, lem, mats, sec = {}, {}, {}, None
    for i, tok in enumerate(toks):
        T = P._norm(tok)
        if T in DIA1 or T in DIA2 or T in P.LINGUAS:
            # só conta seção se vier seguida de número+letra (o menu repete os nomes)
            if i + 2 < len(toks) and re.fullmatch(r'\d{1,2}', toks[i + 1]) and re.fullmatch(r'[A-E]|ANULAD[AO]', toks[i + 2], re.I):
                sec = T
            continue
        if sec and re.fullmatch(r'\d{1,2}', tok) and i + 1 < len(toks) and re.fullmatch(r'[A-E]|ANULAD[AO]', toks[i + 1], re.I):
            n = int(tok); v = 'X' if toks[i + 1].upper().startswith('ANUL') else toks[i + 1].upper()
            if sec in P.LINGUAS:
                lem.setdefault(sec, {}).setdefault(str(100 + n), v)
            else:
                k = n if sec in DIA1 else 100 + n
                gab.setdefault(str(k), v); mats[str(k)] = sec
    if not gab:
        res['log'].append('página encontrada, mas sem gabarito legível'); return res
    final = dt.datetime.fromisoformat(c['final']).replace(tzinfo=BRT)
    res.update({'status': 'definitivo' if agora() >= final else 'preliminar', 'gab': gab, 'lem': lem, 'materias': mats,
                'anuladas': sorted(int(n) for n, v in gab.items() if v == 'X')})
    res['fontes'].append({'tipo': 'oficial', 'nome': 'Coperse/UFRGS · página de gabaritos', 'url': c['url']})
    return res


def h_watch(c, ant):
    """Bancas sem formato conhecido: vigia páginas, lista links de gabarito e tenta ler PDFs com o parser genérico."""
    res = {'fontes': [], 'log': [], 'links': []}
    for pg in c.get('paginas', []):
        links, st = links_da_pagina(pg, c.get('palavras', ['gabarito']))
        if st != 200:
            res['log'].append(f'{pg}: HTTP {st}')
        filtro = [p.lower() for p in c.get('filtro', [])]
        for l in links:
            alvo = (l['url'] + ' ' + l['titulo']).lower()
            if filtro and not all(f in alvo for f in filtro):
                continue
            res['links'].append(dict(l, nome=c.get('banca', '')))
    for l in res['links']:
        if l['url'].lower().split('?')[0].endswith('.pdf'):
            pdf = get_pdf(l['url'])
            if not pdf:
                continue
            g = P.generico('\n'.join(P.pdf_paginas(pdf)), 1, c.get('n', 200), c.get('alts', 'ABCDE'))
            if len(g) >= c.get('n', 40) * 0.8:
                res.update({'status': 'definitivo' if 'definitiv' in (l['url'] + l['titulo']).lower() else 'preliminar',
                            'gab': {str(n): v for n, v in g.items()}, 'anuladas': sorted(n for n, v in g.items() if v == 'X')})
                res['fontes'].append({'tipo': 'oficial', 'nome': f'{c.get("banca", "")} · {l["titulo"] or "gabarito"}', 'url': l['url']})
                break
            res['log'].append(f'PDF sem leitura automática confiável: {l["url"]}')
    return res


HANDLERS = {'nc_ufpr': h_nc_ufpr, 'inep': h_inep, 'ufrgs_html': h_ufrgs, 'watch': h_watch}


def _hash(d):
    d = {k: v for k, v in d.items() if k not in ('verificado', 'log')}
    return hashlib.sha1(json.dumps(d, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--saida', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'gabaritos.json'))
    ap.add_argument('--so', default=None)
    ap.add_argument('--forcar', action='store_true')
    ap.add_argument('--config', default=None, help='outro config.json (testes com o ano passado)')
    a = ap.parse_args()
    global CFG
    if a.config:
        CFG = json.load(open(a.config, encoding='utf-8'))
    ant = {}
    if os.path.exists(a.saida):
        try:
            ant = json.load(open(a.saida, encoding='utf-8'))
        except Exception:
            ant = {}
    out = {'versao': 1, 'gerado_por': 'robo-gabaritos', 'exams': {}}
    hoje = agora()
    for code, c in CFG['exams'].items():
        prev = (ant.get('exams') or {}).get(code, {})
        if a.so and code != a.so:
            out['exams'][code] = prev or {'status': 'aguardando', 'nome': c.get('nome', code), 'log': []}; continue
        inicio = dt.date.fromisoformat(c['a_partir_de'])
        if hoje.date() < inicio and not a.forcar:
            out['exams'][code] = prev or {'status': 'aguardando', 'nome': c.get('nome', code), 'log': [f'robô começa a vigiar em {inicio.isoformat()}']}
            continue
        fim = (prev.get('desde') or {}).get(prev.get('status'))
        if prev.get('status') in ('definitivo', 'oficial') and fim and not a.forcar:
            try:
                parado = (hoje - dt.datetime.fromisoformat(fim)).days >= c.get('parar_apos_dias', 10)
            except Exception:
                parado = False
            if parado:  # gabarito final estável: para de baixar PDFs da banca
                out['exams'][code] = dict(prev, log=[f'gabarito final desde {fim[:10]}; robô parou de conferir esta prova'])
                continue
        try:
            r = HANDLERS[c['tipo']](c, prev)
        except Exception as ex:  # nunca derruba o robô inteiro
            r = {'log': [f'erro: {type(ex).__name__}: {ex}']}
        if 'status' not in r and prev.get('status') not in (None, 'aguardando'):
            # mantém o último gabarito válido se a fonte sumiu/caiu
            keep = {k: prev[k] for k in prev if k not in ('log', 'noticias', 'links')}
            keep.update({k: v for k, v in r.items() if k in ('links',)})
            r = dict(keep, log=r.get('log', []) + ['fonte indisponível agora; mantido o último gabarito'])
        r.setdefault('status', 'aguardando')
        r['nome'] = c.get('nome', code)
        if c.get('noticias'):
            desde = dt.date.fromisoformat(c['provas'][0])
            r['noticias'] = noticias(c['noticias'], desde, c.get('exigir')) or prev.get('noticias', [])
        # registra quando cada gabarito apareceu
        r['desde'] = prev.get('desde', {})
        if r['status'] not in ('aguardando',) and r['status'] not in r['desde']:
            r['desde'][r['status']] = hoje.isoformat(timespec='minutes')
        out['exams'][code] = r
    mudou = _hash(out) != _hash({k: v for k, v in ant.items()}) if ant else True
    velho = True
    if ant.get('verificado'):
        try:
            velho = (hoje - dt.datetime.fromisoformat(ant['verificado'])).total_seconds() > 3 * 3600
        except Exception:
            velho = True
    out['verificado'] = hoje.isoformat(timespec='minutes')
    if mudou or velho or a.forcar:
        os.makedirs(os.path.dirname(os.path.abspath(a.saida)), exist_ok=True)
        json.dump(out, open(a.saida, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('gabaritos.json atualizado', '(mudou)' if mudou else '(batimento)')
    else:
        print('sem mudanças')
    for code, r in out['exams'].items():
        print(f"  {code}: {r.get('status')} · gab={len(r.get('gab', {}))} versoes={len(r.get('versoes', {}))} "
              f"links={len(r.get('links', []))} noticias={len(r.get('noticias', []))} · {'; '.join(r.get('log', []))[:160]}")


if __name__ == '__main__':
    main()
