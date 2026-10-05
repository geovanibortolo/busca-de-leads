"""Envia os leilões coletados para a plataforma do escritório (/api/leiloes/ingest).

Configuração por variáveis de ambiente:
  PLATAFORMA_URL    ex.: https://gestao-bc.onrender.com
  APP_IMPORT_TOKEN  o mesmo token de importação já usado pelo agente do DJEN
"""

import os

import requests

from .relatorio import grupo_modalidade

# Brasília não tem horário de verão desde 2019; as datas dos sites vêm em hora local.
_FUSO = "-03:00"


def _iso(d):
    return d.isoformat(timespec="minutes") + _FUSO if d else None


def item(l):
    return {
        "chave": l.chave(),
        "fonte": l.fonte,
        "url": l.url,
        "uf": l.uf,
        "municipio": l.municipio or None,
        "modalidade": l.modalidade or None,
        "grupo": grupo_modalidade(l.modalidade),
        "titulo": l.titulo or None,
        "area_ha": round(l.area_ha, 2) if l.area_ha else None,
        "avaliacao": l.valor_avaliacao,
        "pracas": [{"n": n, "quando": _iso(q), "valor": v} for n, q, v in l.pracas],
        "ultima_praca": _iso(l.ultima_praca[1]) if l.ultima_praca else None,
        "matricula": l.matricula or None,
        "cartorio": l.cartorio or None,
        "ccir": l.ccir or None,
        "processos": l.processos[:5],
        "devedor": l.devedor or None,
        "devedor_fonte": l.devedor_fonte or None,
        "credor": l.credor or None,
        "titular": l.titular or None,
        "documentos": l.documentos[:6],
        "leiloeiro": l.leiloeiro or None,
        "situacao": l.situacao or None,
        "link_edital": l.link_edital or None,
        "link_matricula": l.link_matricula or None,
        "descricao": (l.descricao or "")[:4000] or None,
        "tambem_em": l.tambem_em,
    }


def enviar(leiloes, url=None, token=None, falhas=None, timeout=180):
    url = (url or os.environ.get("PLATAFORMA_URL", "")).rstrip("/")
    token = token or os.environ.get("APP_IMPORT_TOKEN", "")
    if not url or not token:
        raise RuntimeError("Defina PLATAFORMA_URL e APP_IMPORT_TOKEN para enviar à plataforma.")
    # O Render (plano grátis) dorme; a primeira chamada acorda o serviço.
    try:
        requests.get(f"{url}/api/health", timeout=90)
    except requests.RequestException:
        pass
    r = requests.post(
        f"{url}/api/leiloes/ingest",
        json={"itens": [item(l) for l in leiloes], "falhas": falhas},
        headers={"x-import-token": token},
        timeout=timeout,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"Plataforma respondeu {r.status_code}: {r.text[:300]}")
    return r.json()
