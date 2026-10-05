"""Coletor do Mega Leilões (www.megaleiloes.com.br), categoria Imóveis Rurais.

Listagem por estado: /imoveis/imoveis-rurais/{uf}?pagina=N. A página do lote
traz campos estruturados (div.item > .header/.value): Vara, Processo, Autor,
Réu, Comitente etc., e links diretos para edital, matrícula e laudo em PDF.
"""

import re
from urllib.parse import urlsplit, urlunsplit

from bs4 import BeautifulSoup

from .. import extrair
from ..modelo import Leilao

BASE = "https://www.megaleiloes.com.br"
FONTE = "Mega Leilões"


def _sem_query(url):
    p = urlsplit(url)
    return urlunsplit((p.scheme, p.netloc, p.path, "", ""))


def url_lista(uf, pagina=1):
    url = f"{BASE}/imoveis/imoveis-rurais/{uf.lower()}"
    return url + (f"?pagina={pagina}" if pagina > 1 else "")


def ler_lista(html):
    """Retorna (links dos lotes, total de páginas)."""
    sopa = BeautifulSoup(html, "html.parser")
    links = []
    for a in sopa.select("a.card-title[href]"):
        u = _sem_query(a["href"])
        if u not in links:
            links.append(u)
    m = re.search(r"Página\s*<b>\d+</b>\s*de\s*<b>(\d+)</b>", html)
    return links, int(m.group(1)) if m else 1


def _limpa(s):
    return re.sub(r"\s+", " ", s or "").strip()


def ler_detalhe(html, url, uf):
    sopa = BeautifulSoup(html, "html.parser")
    campos = {}
    for item in sopa.select("div.item"):
        h, v = item.find(class_="header"), item.find(class_="value")
        if h and v:
            campos.setdefault(_limpa(h.get_text(" ")), _limpa(v.get_text(" ")))

    desc_tag = sopa.select_one("#tab-description .content")
    descricao = _limpa(desc_tag.get_text(" ")) if desc_tag else ""
    titulo = _limpa(sopa.find("h1").get_text(" ")) if sopa.find("h1") else ""

    for tag in sopa(["script", "style", "noscript"]):
        tag.decompose()
    texto = _limpa(sopa.get_text(" "))

    m_cod = re.search(r"Código Lote\s+([JX]?\d+)", texto) or re.search(r"-([jx]\d+)$", url)
    codigo = m_cod.group(1).upper() if m_cod else url.rsplit("-", 1)[-1]
    m_mod = re.search(r"\b(Judicial|Extrajudicial|Venda Direta)\s+Leilão\b", texto)
    modalidade = m_mod.group(1) if m_mod else ("Judicial" if codigo.startswith("J") else "Extrajudicial")

    # "Linha Frâncio, ..., Ampére, PR" -> município é o penúltimo item
    loc = [p.strip() for p in campos.get("Localização", "").split(",") if p.strip()]
    municipio = loc[-2] if len(loc) >= 2 and len(loc[-1]) == 2 else (loc[-1] if loc else "")

    leiloeiro = re.split(r"\s+JUCE", campos.get("Leiloeiro", ""))[0].strip()
    m_aval = re.search(r"R\$\s*([\d.]+,\d{2})", campos.get("Valor de Avaliação", ""))

    pdfs = {}
    for a in sopa.find_all("a", href=True):
        href = a["href"]
        if href.lower().endswith(".pdf") and "cdn" in href:
            nome = href.rsplit("/", 1)[-1].lower()
            for chave in ("edital", "matricula", "laudo"):
                if chave in nome:
                    pdfs.setdefault(chave, href)

    l = Leilao(
        fonte=FONTE,
        codigo=codigo,
        url=url,
        uf=uf.upper(),
        modalidade=modalidade,
        titulo=titulo,
        municipio=municipio,
        tipo="Imóvel Rural",
        leiloeiro=leiloeiro,
        area_ha=extrair.area_hectares(titulo),
        valor_avaliacao=extrair.numero_br(m_aval.group(1)) if m_aval else None,
        pracas=extrair.pracas(texto),
        processos=extrair.processos(campos.get("Processo", "")),
        devedor=campos.get("Réu") or campos.get("Executado") or "",
        credor=campos.get("Autor") or campos.get("Exequente") or campos.get("Comitente") or "",
        link_edital=pdfs.get("edital", ""),
        link_matricula=pdfs.get("matricula", ""),
        descricao=descricao,
    )
    if campos.get("Vara"):
        l.descricao = f"Vara: {campos['Vara']}. {descricao}"
    return l.completar(descricao)


def coletar(cliente, ufs, log=print):
    resultado = {}
    for uf in ufs:
        links, pagina, paginas = [], 1, 1
        while pagina <= paginas and pagina <= 30:
            html = cliente.get(url_lista(uf, pagina))
            if not html:
                break
            novos, paginas = ler_lista(html)
            links += [l for l in novos if l not in links]
            pagina += 1
        log(f"{FONTE} {uf.upper()}: {len(links)} lotes")
        for url in links:
            html = cliente.get(url)
            if not html:
                continue
            try:
                resultado[url] = ler_detalhe(html, url, uf)
            except Exception as e:
                log(f"  erro ao ler {url}: {e}")
    return list(resultado.values())
