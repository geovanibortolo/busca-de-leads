"""Registro único de leilão, comum a todas as fontes."""

import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import re

from . import extrair


@dataclass
class Leilao:
    fonte: str
    codigo: str
    url: str
    uf: str
    modalidade: str
    titulo: str = ""
    municipio: str = ""
    tipo: str = ""
    leiloeiro: str = ""
    situacao: str = ""
    area_ha: Optional[float] = None
    valor_avaliacao: Optional[float] = None
    pracas: list = field(default_factory=list)  # [(n, datetime, valor)]
    matricula: str = ""
    cartorio: str = ""
    ccir: str = ""
    processos: list = field(default_factory=list)
    devedor: str = ""
    devedor_fonte: str = ""  # "anúncio" ou "edital"
    credor: str = ""
    titular: str = ""
    documentos: list = field(default_factory=list)  # CPFs/CNPJs citados
    data_inclusao: Optional[datetime] = None
    link_edital: str = ""
    link_matricula: str = ""
    descricao: str = ""
    tambem_em: list = field(default_factory=list)  # outras fontes com o mesmo imóvel

    @property
    def ultima_praca(self):
        return self.pracas[-1] if self.pracas else None

    def completar(self, texto):
        """Preenche, a partir do texto livre, os campos que a fonte não trouxe."""
        self.matricula = self.matricula or extrair.matricula(texto) or ""
        self.cartorio = self.cartorio or extrair.cartorio(texto, f"{self.municipio}/{self.uf}") or ""
        self.ccir = self.ccir or extrair.ccir(texto) or ""
        self.processos = self.processos or extrair.processos(texto)
        self.devedor = self.devedor or extrair.devedor(texto) or ""
        if self.devedor and not self.devedor_fonte:
            self.devedor_fonte = "anúncio"
        self.credor = self.credor or extrair.credor(texto) or ""
        self.titular = self.titular or extrair.titular(texto) or ""
        self.documentos = self.documentos or extrair.documentos(texto)
        if self.area_ha is None:
            self.area_ha = extrair.area_hectares(texto)
        return self

    def chave(self):
        """Identifica o mesmo imóvel anunciado em fontes diferentes."""
        if self.matricula and self.cartorio:
            mat = self.matricula.replace(".", "").lstrip("0")
            cart = re.split(r"[/(]", self.cartorio)[0].strip().lower()
            cart = unicodedata.normalize("NFKD", cart).encode("ascii", "ignore").decode()
            return f"{self.uf}|{mat}|{cart}"
        return f"{self.fonte}|{self.codigo}"


def _edital_bloqueado(url):
    from .edital import pode_baixar

    return not pode_baixar(url)


def _peso(l):
    return sum(bool(x) for x in (l.devedor, l.matricula, l.cartorio, l.processos, l.link_edital,
                                 l.link_matricula, l.pracas, l.area_ha, l.ccir))


def unificar(leiloes):
    """Junta o mesmo imóvel anunciado em várias fontes, mantendo o registro mais completo."""
    grupos = {}
    for l in leiloes:
        grupos.setdefault(l.chave(), []).append(l)
    res = []
    for itens in grupos.values():
        itens.sort(key=_peso, reverse=True)
        base = itens[0]
        for outro in itens[1:]:
            base.tambem_em.append(f"{outro.fonte}: {outro.url}")
            if _edital_bloqueado(base.link_edital) and outro.link_edital and not _edital_bloqueado(outro.link_edital):
                base.link_edital = outro.link_edital
            for campo in ("devedor", "devedor_fonte", "credor", "titular", "ccir", "link_edital",
                          "link_matricula", "valor_avaliacao", "area_ha", "situacao"):
                if not getattr(base, campo) and getattr(outro, campo):
                    setattr(base, campo, getattr(outro, campo))
            if not base.processos:
                base.processos = outro.processos
            base.documentos = list(dict.fromkeys(base.documentos + outro.documentos))
        res.append(base)
    return res
