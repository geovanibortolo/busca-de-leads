"""Relatório HTML (arquivo único, abre no navegador, funciona offline)."""

import json
from datetime import datetime
from pathlib import Path

_MODELO = Path(__file__).with_name("relatorio.html")


def _grupo_modalidade(m):
    m = (m or "").lower()
    if m.startswith("judicial"):
        return "Judicial"
    if m.startswith("extrajudicial"):
        return "Extrajudicial"
    if "pgfn" in m:
        return "PGFN"
    return "Outro"


def _item(l):
    return {
        "fonte": l.fonte,
        "url": l.url,
        "uf": l.uf,
        "municipio": l.municipio or "",
        "modalidade": l.modalidade or "",
        "grupo": _grupo_modalidade(l.modalidade),
        "titulo": l.titulo,
        "area": l.area_ha,
        "avaliacao": l.valor_avaliacao,
        "pracas": [
            {"n": n, "quando": quando.isoformat(timespec="minutes"), "valor": valor}
            for n, quando, valor in l.pracas
        ],
        "matricula": l.matricula,
        "cartorio": l.cartorio,
        "ccir": l.ccir,
        "processos": l.processos[:3],
        "devedor": l.devedor,
        "devedorFonte": l.devedor_fonte,
        "credor": l.credor,
        "titular": l.titular,
        "docs": l.documentos[:4],
        "leiloeiro": l.leiloeiro,
        "situacao": l.situacao,
        "edital": l.link_edital,
        "matriculaPdf": l.link_matricula,
        "descricao": (l.descricao or "")[:1500],
        "tambemEm": l.tambem_em,
    }


def gerar(leiloes, caminho, agora=None):
    agora = agora or datetime.now()
    dados = json.dumps([_item(l) for l in leiloes], ensure_ascii=False)
    dados = dados.replace("</", "<\\/")  # não fechar o <script> por acidente
    html = (
        _MODELO.read_text(encoding="utf-8")
        .replace("__DADOS__", dados)
        .replace("__GERADO__", agora.isoformat(timespec="minutes"))
    )
    Path(caminho).write_text(html, encoding="utf-8")
    return len(leiloes)
