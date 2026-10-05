"""Extração de dados a partir do texto livre dos anúncios de leilão."""

import re
from datetime import datetime

# Número de processo no padrão CNJ: NNNNNNN-DD.AAAA.J.TR.OOOO (com ou sem pontuação)
_CNJ = re.compile(r"\b(\d{7})-?(\d{2})\.?(\d{4})\.?(\d)\.?(\d{2})\.?(\d{4})\b")
# Código do imóvel rural no INCRA (CCIR/SNCR): 000.000.000.000-0
_CCIR = re.compile(r"\b(\d{3}\.\d{3}\.\d{3}\.\d{3}-\d)\b")
_MATRICULA = [
    re.compile(r"matr[ií]cula\s*(?:sob\s*)?(?:n[º°o.]*\s*|-\s*)?(\d{1,3}(?:\.\d{3})+|\d+)", re.I),
    re.compile(r"(?:CRI|Registro de Im[óo]veis)[^.;]{0,40}?sob\s*(?:o\s*)?n[º°o.]*\s*(\d{1,3}(?:\.\d{3})+|\d+)", re.I),
]
_CARTORIO = re.compile(
    r"(?:Registro de Im[óo]veis|CRI|Cart[óo]rio de Registro de Im[óo]veis)"
    r"(?:\s+da)?(?:\s+Comarca)?\s+(?:de|do|da|local)?\s*([A-ZÀ-Ú][\wÀ-ú' ]+?)(?:\s*[-/]\s*([A-Z]{2}))?(?=[\s,.;)]|$)",
    re.I,
)
_PRACA = re.compile(
    r"(\d)\s*[ªº°]\s*Pra[çc]a:?\s*(\d{2}/\d{2}/\d{4})\s*(?:às\s*(\d{2}:\d{2}))?\s*(?:R\$\s*([\d.]+,\d{2}))?",
    re.I,
)
_HECTARES = re.compile(r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?)\s*(?:hectares|ha)\b", re.I)
_ALQUEIRES = re.compile(r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?)\s*alqueires?\s*(paulistas?)?", re.I)
_M2 = re.compile(r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?)\s*(?:m²|m2|metros quadrados)", re.I)

# Padrões que costumam nomear o devedor no texto do anúncio
_PARTES = [
    re.compile(r"\bcontra\s+(.{3,120}?)(?=,\s*este|\s*,?\s*(?:este|o|a)\s+im[óo]vel|[.;]|\s+\(|$)", re.I),
    re.compile(r"\bexecutad[oa]s?\s*:?\s*(.{3,120}?)(?=[.;,(]|\s+-\s|$)", re.I),
    re.compile(r"\bdevedor(?:es)?(?:\s+fiduciante)?s?\s*:?\s*(.{3,120}?)(?=[.;,(]|\s+-\s|$)", re.I),
    re.compile(r"\bfiduciantes?\s*:?\s*(.{3,120}?)(?=[.;,(]|\s+-\s|$)", re.I),
]
_EXEQUENTE = [
    re.compile(r"\brequerid[ao]\s+por\s+(.{3,120}?)\s+contra\b", re.I),
    re.compile(r"\bexequente\s*:?\s*(.{3,120}?)(?=[.;,(]|\s+-\s|$)", re.I),
    re.compile(r"\bcredor(?:a)?(?:\s+fiduci[aá]ri[oa])?\s*:?\s*(.{3,120}?)(?=[.;,(]|\s+-\s|$)", re.I),
]


def numero_br(txt):
    """'1.234.567,89' -> 1234567.89"""
    if not txt:
        return None
    try:
        return float(txt.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def processos(texto):
    vistos = []
    for m in _CNJ.finditer(texto or ""):
        n = "{}-{}.{}.{}.{}.{}".format(*m.groups())
        if n not in vistos:
            vistos.append(n)
    return vistos


def ccir(texto):
    m = _CCIR.search(texto or "")
    return m.group(1) if m else None


def matricula(texto):
    for rx in _MATRICULA:
        m = rx.search(texto or "")
        if m:
            return m.group(1)
    return None


def cartorio(texto, municipio=None):
    m = _CARTORIO.search(texto or "")
    if not m:
        return None
    nome = m.group(1).strip(" -")
    if nome.lower().split()[0] in ("local", "sob", "desta", "nesta"):
        return municipio
    return f"{nome}/{m.group(2)}" if m.group(2) else nome


def pracas(texto):
    """Lista de praças [(numero, datetime, valor)] sem repetição, em ordem."""
    res = {}
    for m in _PRACA.finditer(texto or ""):
        num = int(m.group(1))
        if num in res:
            continue
        quando = datetime.strptime(
            m.group(2) + " " + (m.group(3) or "00:00"), "%d/%m/%Y %H:%M"
        )
        res[num] = (num, quando, numero_br(m.group(4)))
    return [res[k] for k in sorted(res)]


def area_hectares(texto):
    """Área em hectares a partir da descrição (hectares > alqueires > m²)."""
    t = texto or ""
    m = _HECTARES.search(t)
    if m:
        return numero_br(m.group(1))
    m = _ALQUEIRES.search(t)
    if m:
        alq = numero_br(m.group(1))
        # alqueire paulista = 2,42 ha (padrão no PR/SP); outros variam
        return round(alq * 2.42, 2) if alq else None
    m = _M2.search(t)
    if m:
        v = numero_br(m.group(1))
        return round(v / 10000, 2) if v else None
    return None


def _limpa_nome(s):
    s = re.sub(r"\s+", " ", s).strip(" :-–")
    return s if len(s) >= 3 else None


def devedor(texto):
    for rx in _PARTES:
        m = rx.search(texto or "")
        if m:
            nome = _limpa_nome(m.group(1))
            if nome:
                return nome
    return None


def credor(texto):
    for rx in _EXEQUENTE:
        m = rx.search(texto or "")
        if m:
            nome = _limpa_nome(m.group(1))
            if nome:
                return nome
    return None
