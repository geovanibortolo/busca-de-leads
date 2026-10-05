"""Extração de dados a partir do texto livre dos anúncios de leilão."""

import re
from datetime import datetime

# Número de processo no padrão CNJ: NNNNNNN-DD.AAAA.J.TR.OOOO (com ou sem pontuação)
_CNJ = re.compile(r"\b(\d{7})-?(\d{2})\.?(\d{4})\.?(\d)\.?(\d{2})\.?(\d{4})\b")
# Código do imóvel rural no INCRA (CCIR/SNCR): 000.000.000.000-0
_CCIR = re.compile(r"\b(\d{3}\.\d{3}\.\d{3}\.\d{3}-\d)\b")
_DOC = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")

_NUM_MATRICULA = r"(\d{1,3}(?:\.\d{3})+|\d+)"
_MATRICULA = [
    re.compile(r"(?i:matr[ií]cula)\s*(?:(?i:sob)\s*)?(?:(?i:n)[º°o.]*\s*|-\s*|:\s*)?" + _NUM_MATRICULA),
    re.compile(r"(?i:CRI|C\.R\.I\.?|Registro de Im[óo]veis)[^.;]{0,40}?(?i:sob)\s*(?:o\s*)?(?i:n)[º°o.]*\s*" + _NUM_MATRICULA),
    re.compile(r"^\s*(?:(?i:n)[º°o.]*\s*)?" + _NUM_MATRICULA),  # campo "Matrícula:" do site
]
# Depois do número: não pode ser decimal/área ("2.227.500,00 m²")
_NAO_MATRICULA = re.compile(r"^(?:[.,]\d|\s*(?:m²|m2|ha\b|hectares|metros|alqueires))", re.I)

# Nome de cidade: palavras capitalizadas ligadas por de/do/da/dos/das (sensível a maiúsculas)
_CIDADE = r"(?!Registro|Im[óo]veis|Of[íi]cio|Servi[çc]o)([A-ZÀ-Ý][\wÀ-ÿ'´`]+(?:\s+(?:[dD][aeoAEO][sS]?\s+)?[A-ZÀ-Ý][\wÀ-ÿ'´`]+){0,4})"
_CARTORIO = re.compile(
    r"(?i:Registro de Im[óo]veis|C\.?R\.?I\.?|O\.?R\.?I\.?|Cart[óo]rio(?: de Registro de Im[óo]veis)?)"
    r"(?:\s+(?i:da\s+Comarca|do\s+Munic[íi]pio))?\s+(?i:de|do|da)\s+" + _CIDADE +
    r"(?:\s*[-/]\s*([A-Z]{2})\b)?"
)
_PRACA = re.compile(
    r"(\d)\s*[ªº°]\s*(?:Pra[çc]a|Leil[ãa]o):?\s*(\d{2}/\d{2}/\d{4})\s*(?:(?:às|as|-)\s*(\d{2})[:h](\d{2}))?"
    r"(?:[^\d$]{0,40}?R\$\s*([\d.]+,\d{2}))?",
    re.I,
)
_HECTARES = re.compile(r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?)\s*(?:hectares|ha)\b", re.I)
_ALQUEIRES = re.compile(r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?)\s*alqueires?\s*(paulistas?)?", re.I)
_M2 = re.compile(r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?)\s*(?:m²|m2|metros quadrados)", re.I)

# Fim de um campo rotulado: próximo rótulo ("Depositário:", "Vara da Justiça:",
# "OBSERVAÇÃO:"), ";", ". ", "(", ", R.3" (registro na matrícula) ou fim do texto.
# Nomes em CAIXA ALTA com várias palavras não contam como rótulo.
_ROTULOS_CONHECIDOS = (
    r"Depositári[oa]|Bem|Bens|Vara|Comarca|Processo|Autos|Exequente|Executad[oa]|Cidade|Endere[çc]o"
    r"|Visita[çc][ãa]o|Observa[çc][ãa]o|Observa[çc][õo]es|Avalia[çc][ãa]o|[ÔO]nus|Matr[íi]cula|Credor[a]?"
    r"|Devedor|Propriet[áa]ri[oa]|Localiza[çc][ãa]o|Descri[çc][ãa]o|Lote|Valor|Tipo|Data|Autor[a]?|R[ée]u"
    r"|Comitente|Leiloeir[oa]|Magistrad[oa]|Natureza|Classe|Ju[íi]z|Ju[íi]zo|F[óo]rum|Foro|Situa[çc][ãa]o"
    r"|[ÁA]rea|Documentos|Requerente|Requerid[oa]|Interessad[oa]|Credor Fiduci[áa]rio|Fiduciante"
)
_ROTULO_SEGUINTE = (
    r"(?:(?i:" + _ROTULOS_CONHECIDOS + r")(?:\s(?:d[aeo]s?\s)?[\wÁ-ú/]+)?(?:\([a-zA-Z]{1,3}\))?"
    r"|[A-ZÁ-Ú/]{3,}(?:\(S\))?)\s*:"
)
_FIM_CAMPO = (
    r"(?=\s+" + _ROTULO_SEGUINTE + r"|\s*;|\.\s|\s+\(|,\s*(?:R|Av)\.?\s*\d"
    r"|,\s*(?i:executad|devedor|r[ée]u\b|CPF|CNPJ|inscrit|portador)|$)"
)


def _rotulado(rotulos):
    return re.compile(r"\b(?i:" + rotulos + r")(?:\((?i:s|as|os)\))?\s*:\s*(.{3,150}?)" + _FIM_CAMPO)


_DEVEDOR = [
    _rotulado(r"executad[oa]s?|devedor(?:es)?(?:\s+fiduciantes?)?|fiduciantes?|r[ée]u|r[ée]us|requerid[oa]s?"),
    re.compile(r"(?i:pertencente\s+(?:ao|à|aos|às)\s+executad[oa]s?)\s+(.{3,100}?)(?=,|\.\s|$)"),
    re.compile(r"\b(?i:contra)\s+(.{3,120}?)(?=,\s*(?i:este|o)|\s*,?\s*(?i:este|o|a)\s+(?i:im[óo]vel)|[.;]|\s+\(|$)"),
]
_CREDOR = [
    _rotulado(r"exequentes?|credor(?:a|es)?(?:\s+fiduci[aá]ri[oa])?|autor(?:a|es)?|requerentes?|comitente"),
    re.compile(r"\b(?i:requerid[ao]\s+por)\s+(.{3,120}?)\s+(?i:contra)\b"),
]
_TITULAR = re.compile(
    r"(?i:em\s+nome\s+d[eoa]s?|em\s+nome|propriet[áa]ri[oa]s?(?:\s+registral)?\s*:|de\s+propriedade\s+d[eoa]s?)\s*"
    r"([A-ZÀ-Ý][\wÀ-ÿ'. ]{3,80}?)"
    r"(?=\s*[;,(]|\.\s|\s+(?i:CPF|CNPJ|brasileir|nacionalidade|portador|inscrit|casad|solteir)|$)"
)


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


def documentos(texto):
    """CPFs/CNPJs citados no texto (formatados), sem repetição."""
    return list(dict.fromkeys(_DOC.findall(texto or "")))


def matricula(texto):
    t = texto or ""
    for rx in _MATRICULA:
        for m in rx.finditer(t):
            if not _NAO_MATRICULA.match(t[m.end():]):
                return m.group(1)
    return None


def cartorio(texto, municipio=None):
    m = _CARTORIO.search(texto or "")
    if not m:
        return municipio if re.search(r"(?i)CRI\s+local|Registro de Im[óo]veis local", texto or "") else None
    nome = m.group(1).strip()
    return f"{nome}/{m.group(2)}" if m.group(2) else nome


def pracas(texto):
    """Lista de praças [(numero, datetime, valor)] sem repetição, em ordem."""
    res = {}
    for m in _PRACA.finditer(texto or ""):
        num = int(m.group(1))
        if num in res or not 1 <= num <= 3:
            continue
        try:
            quando = datetime.strptime(
                f"{m.group(2)} {m.group(3) or '00'}:{m.group(4) or '00'}", "%d/%m/%Y %H:%M"
            )
        except ValueError:
            continue
        res[num] = (num, quando, numero_br(m.group(5)))
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


_NAO_NOME = re.compile(
    r"^(?:R\$|\d|vara\b|ju[íi]zo|comarca|cart[óo]rio|processo|autos|execu[çc][ãa]o|cumprimento|a\s+fra[çc][ãa]o)", re.I
)


def _limpa_nome(s):
    s = re.sub(r"\s+", " ", s).strip(" :-–,")
    if len(s) < 3 or _NAO_NOME.search(s):
        return None
    return s


def _primeiro(regexes, texto):
    for rx in regexes:
        for m in rx.finditer(texto or ""):
            nome = _limpa_nome(m.group(1))
            if nome:
                return nome
    return None


def devedor(texto):
    return _primeiro(_DEVEDOR, texto)


def credor(texto):
    return _primeiro(_CREDOR, texto)


def titular(texto):
    """Titular citado na matrícula/CCIR ("em nome de ...", "Proprietário: ...")."""
    return _primeiro([_TITULAR], texto)
