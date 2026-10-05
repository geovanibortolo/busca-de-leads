"""Uso: python -m leiloes --ufs PR SC RS   (gera saida/leiloes_rurais_AAAA-MM-DD.html e .xlsx)"""

import argparse
from datetime import datetime
from pathlib import Path

from . import edital, enviar, planilha, relatorio
from .fontes import leilaodefazenda, leiloesjudiciais, megaleiloes, zuk
from .http import Cliente
from .modelo import unificar

FONTES = {
    "fazendas": "Leilão de Fazendas",
    "mega": "Mega Leilões",
    "zuk": "Portal Zuk",
    "judiciais": "Leilões Judiciais",
}


def main():
    ap = argparse.ArgumentParser(description="Busca leilões de imóveis rurais e gera planilha de leads.")
    ap.add_argument("--ufs", nargs="+", default=["PR", "SC", "RS"])
    ap.add_argument("--fontes", nargs="+", default=list(FONTES), choices=list(FONTES))
    ap.add_argument(
        "--modalidades",
        nargs="+",
        default=leilaodefazenda.MODALIDADES_PADRAO,
        help="(Leilão de Fazendas) códigos do filtro do site: "
        + ", ".join(f"{k}={v}" for k, v in leilaodefazenda.MODALIDADES.items()),
    )
    ap.add_argument("--saida", default=None,
                    help="Caminho base dos arquivos, sem extensão (padrão: saida/leiloes_rurais_AAAA-MM-DD)")
    ap.add_argument("--formatos", nargs="+", default=["html", "xlsx"], choices=["html", "xlsx"])
    ap.add_argument("--incluir-encerrados", action="store_true", help="Mantém leilões cujas praças já passaram")
    ap.add_argument("--sem-edital", action="store_true", help="Não baixa editais em PDF para achar o devedor")
    ap.add_argument("--intervalo", type=float, default=1.5, help="Segundos entre requisições")
    ap.add_argument("--enviar", action="store_true",
                    help="Envia os leilões à plataforma (usa PLATAFORMA_URL e APP_IMPORT_TOKEN do ambiente)")
    args = ap.parse_args()

    saida = Path(args.saida or f"saida/leiloes_rurais_{datetime.now():%Y-%m-%d}")
    saida = saida.with_suffix("") if saida.suffix in (".xlsx", ".html") else saida
    saida.parent.mkdir(parents=True, exist_ok=True)
    cliente = Cliente(intervalo=args.intervalo)

    leiloes = []
    if "fazendas" in args.fontes:
        leiloes += leilaodefazenda.coletar(cliente, args.ufs, args.modalidades)
    if "mega" in args.fontes:
        leiloes += megaleiloes.coletar(cliente, args.ufs)
    if "zuk" in args.fontes:
        leiloes += zuk.coletar(cliente, args.ufs)
    if "judiciais" in args.fontes:
        leiloes += leiloesjudiciais.coletar(cliente, args.ufs)

    total = len(leiloes)
    leiloes = unificar(leiloes)
    print(f"{total} anúncios -> {len(leiloes)} imóveis distintos")
    if not args.incluir_encerrados:
        leiloes = planilha.ativos(leiloes)

    if not args.sem_edital:
        faltando = [l for l in leiloes if not l.devedor and edital.pode_baixar(l.link_edital)]
        achados = sum(edital.completar(cliente, l) for l in faltando)
        print(f"Editais lidos: devedor encontrado em {achados} de {len(faltando)} editais baixáveis sem nome no anúncio")

    if args.enviar:
        r = enviar.enviar(leiloes)
        print(f"Plataforma: {r.get('recebidos')} recebidos, {r.get('novos')} novos, {r.get('atualizados')} atualizados")

    if "html" in args.formatos:
        n = relatorio.gerar(leiloes, saida.with_suffix(".html"))
        print(f"{n} leilões no relatório {saida.with_suffix('.html')}")
    if "xlsx" in args.formatos:
        n = planilha.gerar(leiloes, saida.with_suffix(".xlsx"))
        print(f"{n} leilões na planilha {saida.with_suffix('.xlsx')}")


if __name__ == "__main__":
    main()
