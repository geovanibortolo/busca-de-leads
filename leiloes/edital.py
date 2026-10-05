"""Leitura dos editais em PDF para achar executado/devedor quando o anúncio não traz.

Só baixa PDFs de hosts que permitem robôs (lista abaixo). Os demais ficam como
link na planilha para abrir manualmente. Editais de leilão com vários
lotes listam várias partes; escolhemos a ocorrência mais próxima (antes) do
processo ou da matrícula do lote.
"""

import io
import re
import shutil
import subprocess
from urllib.parse import urlsplit

# Hosts cujos PDFs podemos baixar automaticamente. Ficam de fora, por exemplo:
# file.leilaoimovel.com.br (desafio anti-robô da Cloudflare),
# documentacaoleilao.portalzuk.com.br e cdn1.megaleiloes.com.br (robots.txt: Disallow: /).
HOSTS_PERMITIDOS = ("s3-sa-east-1.amazonaws.com", "s3.sa-east-1.amazonaws.com")


def pode_baixar(url):
    host = urlsplit(url or "").netloc.lower()
    return host in HOSTS_PERMITIDOS


_DEVEDOR_PDF = re.compile(
    r"\b(?i:executad[oa]s?|devedor(?:es)?(?:\s+fiduciantes?)?|fiduciantes?|r[ée]us?)(?:\((?i:s|as|os)\))?"
    r"\s*:?\s+(?:\(?(?i:a|o|as|os)\)?\s+)?"
    r"([A-ZÀ-Ý][A-ZÀ-Ý0-9 .,&/'´-]{3,150}?)"
    r"(?=\s*\(|\s*,\s*(?i:inscrit|portador|CPF|CNPJ|credor|bem\b|com\b|brasileir|casad|solteir|na\s+pessoa)|\s+(?i:CPF|CNPJ)|\.\s|;|\n|$)"
)
_CREDOR_PDF = re.compile(
    r"\b(?i:exequentes?|credor(?:a|es)?(?:\s+fiduci[áa]ri[oa])?|autor(?:a|es)?|requerid[oa]\s+por)(?:\((?i:s|as|os)\))?"
    r"\s*:?\s+([A-ZÀ-Ý][A-ZÀ-Ý0-9 .,&/'´-]{3,150}?)"
    r"(?=\s*\(|\s*,\s*(?i:inscrit|CPF|CNPJ)|\s+(?i:CPF|CNPJ)|\.\s|;|\n|$)"
)
_DOC_PERTO = re.compile(r"(?i:CPF|CNPJ)[^\d]{0,15}(\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})")


def texto_pdf(dados):
    """Texto do PDF: pdftotext se instalado (melhor layout), senão pypdf."""
    if not dados:
        return ""
    if shutil.which("pdftotext"):
        r = subprocess.run(["pdftotext", "-layout", "-", "-"], input=dados, capture_output=True, timeout=120)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.decode("utf-8", errors="replace")
    try:
        from pypdf import PdfReader

        return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(dados)).pages)
    except Exception:
        return ""


def _mais_proxima(ocorrencias, ancora):
    if not ocorrencias:
        return None
    if ancora is None or len(ocorrencias) == 1:
        return ocorrencias[0]
    antes = [m for m in ocorrencias if m.start() <= ancora]
    return antes[-1] if antes else ocorrencias[0]


def partes(texto, processos=(), matricula=""):
    """(devedor, credor, documentos do devedor) extraídos do edital."""
    t = re.sub(r"[ \t]+", " ", texto or "")
    ancora = None
    for chave in list(processos) + ([matricula] if matricula else []):
        i = t.find(chave)
        if i >= 0:
            ancora = i
            break
    dev = _mais_proxima(list(_DEVEDOR_PDF.finditer(t)), ancora)
    cred = _mais_proxima(list(_CREDOR_PDF.finditer(t)), ancora)
    devedor = re.sub(r"\s+", " ", dev.group(1)).strip(" ,.-") if dev else ""
    credor = re.sub(r"\s+", " ", cred.group(1)).strip(" ,.-") if cred else ""
    docs = []
    if dev:
        docs = [m.group(1) for m in _DOC_PERTO.finditer(t[dev.end(): dev.end() + 120])][:1]
    return devedor, credor, docs


def completar(cliente, leilao):
    """Preenche devedor/credor/documentos a partir do edital, se faltarem."""
    url = leilao.link_edital
    if leilao.devedor or not pode_baixar(url):
        return False
    try:
        dados = cliente.get_bytes(url)
    except RuntimeError:
        return False
    dev, cred, docs = partes(texto_pdf(dados), leilao.processos, leilao.matricula)
    if dev:
        leilao.devedor = dev
        leilao.credor = leilao.credor or cred
        leilao.documentos = list(dict.fromkeys(docs + leilao.documentos))
        leilao.devedor_fonte = "edital"
    return bool(dev)
