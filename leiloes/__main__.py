"""Uso: python -m leiloes --ufs PR SC RS --saida saida/leiloes_rurais.xlsx"""

import argparse
from datetime import datetime
from pathlib import Path

from . import planilha
from .fontes import leilaodefazenda
from .http import Cliente


def main():
    ap = argparse.ArgumentParser(description="Busca leilões de imóveis rurais e gera planilha de leads.")
    ap.add_argument("--ufs", nargs="+", default=["PR", "SC", "RS"])
    ap.add_argument(
        "--modalidades",
        nargs="+",
        default=leilaodefazenda.MODALIDADES_PADRAO,
        help="Códigos do filtro do site: "
        + ", ".join(f"{k}={v}" for k, v in leilaodefazenda.MODALIDADES.items()),
    )
    ap.add_argument("--saida", default=None, help="Caminho do .xlsx (padrão: saida/leiloes_rurais_AAAA-MM-DD.xlsx)")
    ap.add_argument("--incluir-encerrados", action="store_true", help="Mantém leilões cujas praças já passaram")
    ap.add_argument("--intervalo", type=float, default=1.5, help="Segundos entre requisições")
    args = ap.parse_args()

    saida = Path(args.saida or f"saida/leiloes_rurais_{datetime.now():%Y-%m-%d}.xlsx")
    saida.parent.mkdir(parents=True, exist_ok=True)

    cliente = Cliente(intervalo=args.intervalo)
    leiloes = leilaodefazenda.coletar(cliente, args.ufs, args.modalidades)
    if not args.incluir_encerrados:
        leiloes = planilha.ativos(leiloes)
    n = planilha.gerar(leiloes, saida)
    print(f"{n} leilões gravados em {saida}")


if __name__ == "__main__":
    main()
