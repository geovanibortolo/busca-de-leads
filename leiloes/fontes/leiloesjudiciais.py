"""Coletor do Leilões Judiciais (www.leiloesjudiciais.com.br).

Lista por estado em /imoveis/fazendas-sitios-e-chacaras/{uf} (todos os lotes
numa página só; o robots.txt proíbe ?pagina=). A página do lote traz a
descrição, as datas de encerramento e os anexos (edital, matrícula, avaliação)
em PDF num bucket S3 público.
"""

import re
from datetime import datetime

from bs4 import BeautifulSoup

from .. import extrair
from ..modelo import Leilao

BASE = "https://www.leiloesjudiciais.com.br"
FONTE = "Leilões Judiciais"


def url_lista(uf):
    return f"{BASE}/imoveis/fazendas-sitios-e-chacaras/{uf.lower()}"


def ler_lista(html):
    return [BASE + l for l in dict.fromkeys(re.findall(r'href="(/lote/\d+/\d+)"', html))]


def _limpa(s):
    return re.sub(r"\s+", " ", s or "").strip()


def _anexos(html):
    """{'EDITAL': url, 'MATRÍCULA': url, ...} a partir do estado da página (Nuxt)."""
    res = {}
    for nome, url in re.findall(r'"([^"]{2,60})","(https://s3[^"]+/anexo/[^"]+\.pdf)"', html):
        res.setdefault(nome.upper(), url)
    return res


def ler_detalhe(html, url, uf):
    anexos = _anexos(html)
    sopa = BeautifulSoup(html, "html.parser")
    for tag in sopa(["script", "style", "noscript"]):
        tag.decompose()
    texto = _limpa(sopa.get_text(" "))

    m_tit = re.search(r"Compartilhar\s+(.{5,200}?)\s+Descrição do Lote", texto)
    titulo = m_tit.group(1) if m_tit else ""
    ini = texto.find("Descrição do Lote")
    fim = texto.find("Documentos", ini)
    descricao = texto[ini + len("Descrição do Lote"):fim if fim > ini else None].strip() if ini >= 0 else ""

    m_id = re.search(r"\bID\s+(\d+)\s+(Judicial|Extrajudicial|Venda Direta)", texto)
    modalidade = m_id.group(2) if m_id else ""

    # "1º Encerramento - 14/10/2026 16:00" equivale às praças; "Ciclos" são repasses posteriores
    pracas = []
    for n, d, h in re.findall(r"(\d)º Encerramento\s*-\s*(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})", texto):
        pracas.append((int(n), datetime.strptime(f"{d} {h}", "%d/%m/%Y %H:%M"), None))
    pracas = sorted(set(pracas))
    m_min = re.search(r"Lance mínimo atual:\s*R\$\s*([\d.]+,\d{2})", texto)
    m_prox = re.search(r"L\.Mín \(Próxima Etapa\):\s*R\$\s*([\d.]+,\d{2})", texto)
    if pracas:
        pracas[0] = (pracas[0][0], pracas[0][1], extrair.numero_br(m_min.group(1)) if m_min else None)
    if len(pracas) > 1 and m_prox:
        pracas[1] = (pracas[1][0], pracas[1][1], extrair.numero_br(m_prox.group(1)))

    m_aval = re.search(r"Avaliação:\s*R\$\s*([\d.]+,\d{2})", texto)
    m_loc = re.search(r"Lances\s+\d+\s+([^/]{2,40}?)/([A-Z]{2})\s+Avalia", texto) or re.search(
        r"-\s*([^-/]+)/([A-Z]{2})\s*$", titulo)
    m_leil = re.search(r"-\d+%\s+(.{5,60}?)\s+(?:Para participar|Leiloeir|Matr[íi]cula JUC|JUCE)", texto)

    l = Leilao(
        fonte=FONTE,
        codigo=url.rstrip("/").rsplit("/", 1)[-1],
        url=url,
        uf=uf.upper(),
        modalidade=modalidade,
        titulo=titulo,
        municipio=m_loc.group(1).strip() if m_loc else "",
        tipo="Fazenda/Sítio/Chácara",
        leiloeiro=m_leil.group(1).strip() if m_leil else "",
        area_ha=extrair.area_hectares(titulo),
        valor_avaliacao=extrair.numero_br(m_aval.group(1)) if m_aval else None,
        pracas=pracas,
        link_edital=anexos.get("EDITAL", ""),
        link_matricula=anexos.get("MATRÍCULA", "") or anexos.get("MATRICULA", ""),
        descricao=descricao,
    )
    return l.completar(descricao)


def coletar(cliente, ufs, log=print):
    res = {}
    for uf in ufs:
        html = cliente.get(url_lista(uf))
        links = ler_lista(html) if html else []
        log(f"{FONTE} {uf.upper()}: {len(links)} lotes")
        for url in links:
            if url in res:
                continue
            det = cliente.get(url)
            if not det:
                continue
            try:
                res[url] = ler_detalhe(det, url, uf)
            except Exception as e:
                log(f"  erro ao ler {url}: {e}")
    return list(res.values())
