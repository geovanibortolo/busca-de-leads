"""Coletor do Portal Zuk (www.portalzuk.com.br).

Usa a vitrine de imóveis rurais e as vitrines por estado (/u/todos-imoveis/{uf}),
filtrando os cartões rurais. O botão "carregar mais" usa rotas AJAX que o
robots.txt do site proíbe, então ficam só os lotes da primeira carga de cada
vitrine. Também não acessamos /edital (proibido no robots.txt).
"""

import re

from bs4 import BeautifulSoup

from .. import extrair
from ..modelo import Leilao

BASE = "https://www.portalzuk.com.br"
FONTE = "Portal Zuk"
VITRINE_RURAL = f"{BASE}/leilao-de-imoveis/t/todos-imoveis/rurais"
_RURAL = re.compile(r"rural|fazenda|s[íi]tio|ch[áa]cara|gleba", re.I)


def url_estado(uf):
    return f"{BASE}/leilao-de-imoveis/u/todos-imoveis/{uf.lower()}"


def _limpa(s):
    return re.sub(r"\s+", " ", s or "").strip()


def ler_cartoes(html):
    """Cartões da vitrine: dict com url, uf, municipio, tipo, comitente, area, pracas."""
    sopa = BeautifulSoup(html, "html.parser")
    res = []
    for card in sopa.select("div.card-property"):
        a = card.select_one('a[href*="/imovel/"]')
        if not a:
            continue
        url = a["href"].split("?")[0]
        m_uf = re.search(r"/imovel/([a-z]{2})/", url)
        titulo = _limpa(a.get("title", ""))
        tipo = _limpa(card.select_one(".card-property-price-lote").get_text(" ")) if card.select_one(
            ".card-property-price-lote") else ""
        end = card.select_one(".card-property-address a")
        municipio = _limpa(end.get_text(" ")).split("/")[0].strip() if end else ""
        m_com = re.search(r"-\s*([^-|]+?)\s*\|\s*Z\d+", titulo)
        area_txt = " ".join(_limpa(x.get_text(" ")) for x in card.select(".card-property-info-label"))

        pracas = []
        for li in card.select("li.card-property-price"):
            rot = li.select_one(".card-property-price-label")
            val = li.select_one(".card-property-price-value")
            dat = li.select_one(".card-property-price-data")
            if not (dat and val):
                continue
            m_n = re.search(r"(\d)\s*º", rot.get_text(" ") if rot else "")
            m_d = re.search(r"(\d{2}/\d{2}/\d{4})\s*às\s*(\d{2}:\d{2})", dat.get_text(" "))
            m_v = re.search(r"([\d.]+,\d{2})", val.get_text(" "))
            if m_d:
                from datetime import datetime
                quando = datetime.strptime(f"{m_d.group(1)} {m_d.group(2)}", "%d/%m/%Y %H:%M")
                pracas.append((int(m_n.group(1)) if m_n else len(pracas) + 1, quando,
                               extrair.numero_br(m_v.group(1)) if m_v else None))
        res.append({
            "url": url,
            "uf": m_uf.group(1).upper() if m_uf else "",
            "municipio": municipio,
            "tipo": tipo,
            "titulo": titulo,
            "comitente": m_com.group(1).strip() if m_com else "",
            "area_ha": extrair.area_hectares(area_txt),
            "pracas": sorted(pracas),
        })
    return res


def eh_rural(cartao):
    return bool(_RURAL.search(cartao["tipo"])) or "/zona-rural/" in cartao["url"]


def _modalidade(comitente, texto):
    if re.search(r"tribunal|justi[çc]a|judicial|vara\b|TJ[A-Z]{2}", comitente, re.I):
        return "Judicial"
    if re.search(r"aliena[çc][ãa]o fiduci[áa]ria", texto, re.I):
        return "Extrajudicial (alienação fiduciária)"
    if re.search(r"banco|sicoob|sicredi|cooperativa|securitizadora|cr[ée]dit|cons[óo]rcio", comitente, re.I):
        return "Extrajudicial"
    return "Outro"


def ler_detalhe(html, cartao):
    sopa = BeautifulSoup(html, "html.parser")
    pdfs = [a["href"] for a in sopa.find_all("a", href=True) if "documentacaoleilao" in a["href"]]
    for tag in sopa(["script", "style", "noscript"]):
        tag.decompose()
    texto = _limpa(sopa.get_text(" "))

    ini = texto.find("Descrição do imóvel")
    fim = min([i for i in (texto.find(k, ini) for k in ("Veja também", "Formas de pagamento", "Leia Mais"))
               if i > ini] or [len(texto)])
    descricao = texto[ini + len("Descrição do imóvel"):fim].strip() if ini >= 0 else ""
    descricao = descricao.replace(" Acessar processo", "")

    situacao = "Ocupado" if "Imóvel ocupado" in texto else ("Desocupado" if "Imóvel desocupado" in texto else "")
    m_cod = re.search(r"\bZ-(\d+-\d+)\b", texto)
    m_mat = re.search(r"Matrícula do imóvel:\s*([\d.]+)\s*(?:do|da)?\s*(.{0,60}?)(?=\s+Processo:|\s+Observações|$)",
                      descricao)

    l = Leilao(
        fonte=FONTE,
        codigo=m_cod.group(1) if m_cod else cartao["url"].rsplit("/", 1)[-1],
        url=cartao["url"],
        uf=cartao["uf"],
        modalidade=_modalidade(cartao["comitente"], texto),
        titulo=cartao["titulo"],
        municipio=cartao["municipio"],
        tipo=cartao["tipo"],
        leiloeiro="Zuk",
        situacao=situacao,
        area_ha=cartao["area_ha"],
        pracas=cartao["pracas"],
        matricula=m_mat.group(1) if m_mat else "",
        cartorio=_limpa(re.sub(r"^\d+[ºª°]?\s*(?:CRI|C\.R\.I\.?|Registro de Im[óo]veis)?\s*(?:-|de|do)?\s*", "", m_mat.group(2))).replace(" /", "/") if m_mat else "",
        credor=cartao["comitente"],
        link_edital=pdfs[0] if pdfs else "",
        descricao=descricao,
    )
    return l.completar(descricao)


def coletar(cliente, ufs, log=print):
    ufs = {u.upper() for u in ufs}
    cartoes = {}
    for url in [VITRINE_RURAL] + [url_estado(u) for u in sorted(ufs)]:
        html = cliente.get(url)
        if not html:
            continue
        for c in ler_cartoes(html):
            if c["uf"] in ufs and eh_rural(c):
                cartoes.setdefault(c["url"], c)
    log(f"{FONTE} {'/'.join(sorted(ufs))}: {len(cartoes)} lotes rurais")
    res = []
    for c in cartoes.values():
        html = cliente.get(c["url"])
        if not html:
            continue
        try:
            res.append(ler_detalhe(html, c))
        except Exception as e:
            log(f"  erro ao ler {c['url']}: {e}")
    return res
