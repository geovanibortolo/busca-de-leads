"""Coletor do site Leilão de Fazendas (www.leilaodefazenda.com.br).

O site agrega leilões rurais de dezenas de leiloeiros. A listagem por estado
aceita o filtro `venda` (modalidade) e paginação `pag`, 20 itens por página.
"""

import re
from datetime import datetime

from bs4 import BeautifulSoup

from .. import extrair
from ..modelo import Leilao

BASE = "https://www.leilaodefazenda.com.br"
FONTE = "Leilão de Fazendas"

# Valores do filtro "venda" do próprio site
MODALIDADES = {
    "3": "Judicial",
    "4": "Extrajudicial",
    "5": "Outro",
    "12": "PGFN (Comprei)",
    "8": "Venda Direta",
    "11": "Leilão SFI Caixa",
    "1": "Venda Direta Online",
}
# Venda direta = imóvel já perdido pelo devedor; fica de fora por padrão
MODALIDADES_PADRAO = ["3", "4", "5"]

_ROTULOS = [
    "Localização", "Precisão da geolocalização", "Tipo", "Leiloeiro", "Código Imóvel",
    "Valor de Avaliação", "Data de Inclusão", "Matrícula", "Comarca", "Ofício",
    "Descrição", "Observação",
]
_FIM_DETALHES = re.compile(r"\s(?:Valor avaliado|Valor do Imóvel|Considerações Legais)\s")


def url_lista(uf, modalidade, pagina=1):
    url = f"{BASE}/leilao-de-imoveis/{uf.lower()}?s=&venda={modalidade}"
    return url + (f"&pag={pagina}" if pagina > 1 else "")


def ler_lista(html):
    """Retorna (links dos imóveis, total de itens informado pelo site)."""
    links = list(dict.fromkeys(re.findall(r'href="(/imovel/[^"]+)"', html)))
    m = re.search(r"'itens_returned':\s*(\d+)", html)
    total = int(m.group(1)) if m else len(links)
    return [BASE + l for l in links], total


def _campos(texto):
    """Separa o bloco 'Mais sobre o Imóvel' em {rótulo: valor}."""
    ini = texto.find("Mais sobre o Imóvel")
    if ini < 0:
        return {}
    bloco = texto[ini:]
    fim = _FIM_DETALHES.search(bloco)
    if fim:
        bloco = bloco[: fim.start()]
    padrao = re.compile(r"\b(" + "|".join(map(re.escape, _ROTULOS)) + r"):")
    partes = padrao.split(bloco)
    campos = {}
    for i in range(1, len(partes) - 1, 2):
        rot, val = partes[i], partes[i + 1].strip()
        campos.setdefault(rot, val)
    return campos


def ler_detalhe(html, url, uf, modalidade):
    sopa = BeautifulSoup(html, "html.parser")
    for tag in sopa(["script", "style", "noscript"]):
        tag.decompose()
    texto = re.sub(r"\s+", " ", sopa.get_text(" "))
    c = _campos(texto)

    codigo = (c.get("Código Imóvel") or "").split(" ")[0] or url.rsplit("-", 1)[-1]
    # "PR /Guarapuava /Boqueirão" -> "Guarapuava"
    partes_loc = [p.strip() for p in c.get("Localização", "").split("/")]
    municipio = partes_loc[1] if len(partes_loc) > 1 else partes_loc[0]
    tipo = c.get("Tipo", "")
    leiloeiro = re.sub(r"\s*\(Ver An[uú]ncio.*", "", c.get("Leiloeiro", "")).strip()

    descricao = " ".join(x for x in (c.get("Descrição"), c.get("Observação")) if x)
    titulo_tag = sopa.find("h1") or sopa.find("title")
    titulo = re.sub(r"\s+", " ", titulo_tag.get_text(" ")).strip() if titulo_tag else ""

    m_sit = re.search(r"Situação:\s*(Ocupado|Desocupado)", texto)
    m_area = re.search(r"Área Total:\s*([\d.,]+)\s*m²", texto)
    # "Área Total" do site é confiável quando vem em m² de verdade; alguns
    # anúncios informam hectares com o rótulo m² (ex.: "29,50 m²" = 29,5 ha)
    area_site = extrair.numero_br(m_area.group(1)) if m_area else None
    if area_site and area_site >= 1000:
        area = round(area_site / 10000, 2)
    else:
        area = extrair.area_hectares(descricao) or area_site

    mod_tipo = tipo.split("/")[-1].strip() if "/" in tipo else ""
    links = dict(
        (nome, href)
        for href, nome in re.findall(
            r'href="([^"]+)"[^>]*?data-matomo-name="(edital-link|matricula-link)"', html, re.S
        )
    )
    data_inc = None
    if c.get("Data de Inclusão"):
        try:
            data_inc = datetime.strptime(c["Data de Inclusão"][:10], "%d/%m/%Y")
        except ValueError:
            pass

    # Campos "Matrícula:"/"Comarca:" do site às vezes emendam o texto seguinte
    matricula = extrair.matricula(c.get("Matrícula", "")) or ""
    comarca = re.split(r"\s+[A-ZÁ-Ú][\wÁ-ú]+(?:\s[\wÁ-ú]+){0,2}:", c.get("Comarca", ""))[0].strip()
    cartorio = extrair.cartorio(descricao, f"{municipio}/{uf.upper()}")
    if not cartorio and comarca:
        cartorio = comarca + (f" ({c['Ofício'][:3].strip()}º Ofício)" if c.get("Ofício") else "")

    return Leilao(
        fonte=FONTE,
        codigo=codigo,
        url=url,
        uf=uf.upper(),
        modalidade=mod_tipo or MODALIDADES.get(modalidade, modalidade),
        titulo=titulo,
        municipio=municipio,
        tipo=tipo.split("/")[0].strip(),
        leiloeiro=leiloeiro,
        situacao=m_sit.group(1) if m_sit else "",
        area_ha=area,
        valor_avaliacao=extrair.numero_br(
            re.sub(r"[^\d.,]", "", c.get("Valor de Avaliação", "")) or None
        ),
        pracas=extrair.pracas(texto),
        matricula=matricula,
        cartorio=cartorio or "",
        data_inclusao=data_inc,
        link_edital=links.get("edital-link", ""),
        link_matricula=links.get("matricula-link", ""),
        descricao=descricao,
    ).completar(descricao)


def coletar(cliente, ufs, modalidades=None, log=print):
    modalidades = modalidades or MODALIDADES_PADRAO
    resultado = {}
    for uf in ufs:
        for mod in modalidades:
            pagina, links = 1, []
            while True:
                html = cliente.get(url_lista(uf, mod, pagina))
                if not html:
                    break
                novos, total = ler_lista(html)
                links += [l for l in novos if l not in links]
                if not novos or len(links) >= total or pagina >= 50:
                    break
                pagina += 1
            log(f"{uf.upper()} / {MODALIDADES.get(mod, mod)}: {len(links)} imóveis")
            for url in links:
                if url in resultado:
                    continue
                html = cliente.get(url)
                if not html:
                    continue
                try:
                    resultado[url] = ler_detalhe(html, url, uf, mod)
                except Exception as e:  # um anúncio quebrado não derruba a coleta
                    log(f"  erro ao ler {url}: {e}")
    return list(resultado.values())
