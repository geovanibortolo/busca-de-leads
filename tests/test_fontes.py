from datetime import datetime
from pathlib import Path

from leiloes import edital, extrair
from leiloes.fontes import leilaodefazenda, leiloesjudiciais, megaleiloes, zuk
from leiloes.modelo import unificar

FIX = Path(__file__).parent / "fixtures"


def _ler(nome):
    return (FIX / nome).read_text(encoding="utf-8", errors="ignore")


def test_mega():
    links, paginas = megaleiloes.ler_lista(_ler("mega_lista_pr.html"))
    assert len(links) == 1 and paginas == 1
    l = megaleiloes.ler_detalhe(_ler("mega_detalhe.html"), links[0], "pr")
    assert l.codigo == "J129557" and l.modalidade == "Judicial"
    assert l.municipio == "Ampére" and l.area_ha == 1.61
    assert l.processos[0] == "0029176-44.2025.8.26.0100"
    assert l.devedor == "GRUPO LBR" and l.matricula == "7.598"
    assert [p[0] for p in l.pracas] == [1, 2, 3] and l.pracas[1][2] == 492087.55
    assert "edital" in l.link_edital and "matricula" in l.link_matricula


def test_zuk():
    cartoes = zuk.ler_cartoes(_ler("zuk_vitrine_rural.html"))
    c = next(c for c in cartoes if "adrianopolis" in c["url"])
    assert zuk.eh_rural(c) and c["uf"] == "PR" and c["area_ha"] == 7744.0
    assert c["pracas"][1][1] == datetime(2026, 10, 6, 11, 40)
    l = zuk.ler_detalhe(_ler("zuk_detalhe.html"), c)
    assert l.modalidade == "Judicial" and l.matricula == "3.006"
    assert l.cartorio == "Bocaiúva do Sul/PR"
    assert l.processos == ["1070231-29.2023.8.26.0002"]
    assert l.link_edital.endswith(".pdf")


def test_leiloes_judiciais():
    links = leiloesjudiciais.ler_lista(_ler("lj_lista_pr.html"))
    assert len(links) == 11
    l = leiloesjudiciais.ler_detalhe(_ler("lj_detalhe.html"), "https://x/lote/99790/218267", "pr")
    assert l.modalidade == "Judicial" and l.municipio == "Pinhão" and l.area_ha == 484.72
    assert l.matricula == "243" and l.processos[0] == "0001070-08.2009.8.16.0134"
    assert l.pracas[0][1] == datetime(2026, 10, 14, 16, 0) and l.pracas[1][2] == 5429148.75
    assert l.link_edital.endswith(".pdf") and l.link_matricula.endswith(".pdf")


def test_unificar_mesmo_imovel_em_duas_fontes():
    a = leilaodefazenda.ler_detalhe(_ler("ldf_detalhe_ampere.html"), "https://a", "pr", "3")
    b = megaleiloes.ler_detalhe(_ler("mega_detalhe.html"), "https://b-j129557", "pr")
    res = unificar([a, b])
    assert len(res) == 1 and len(res[0].tambem_em) == 1


def test_partes_no_edital():
    texto = (
        "EDITAL ... Processo 0001070-08.2009.8.16.0134\n"
        "EXEQUENTE: CLARI GUSSI (CPF: 338.551.969-15)\n"
        "EXECUTADO: INDÚSTRIAS JOÃO JOSÉ ZATTAR (CNPJ: 76.498.146/0001-70)\n"
    )
    dev, cred, docs = edital.partes(texto)
    assert dev == "INDÚSTRIAS JOÃO JOSÉ ZATTAR" and cred == "CLARI GUSSI"
    assert docs == ["76.498.146/0001-70"]
    dev, _, docs = edital.partes(
        "Ficam intimados o(s) executado(s) SELECT INVESTIMENTOS S/A (CNPJ: 00.340.355/0001-20), credores X"
    )
    assert dev == "SELECT INVESTIMENTOS S/A" and docs == ["00.340.355/0001-20"]


def test_rotulos_com_nomes_em_caixa_alta():
    assert extrair.devedor("Exequente: RISA S/A Executado: LAIRES BODANESE JUNIOR Depositário: x") == "LAIRES BODANESE JUNIOR"
    assert extrair.devedor("Executado(s): Jab Materiais Elétricos Ltda Bem(ns): 01 terreno") == "Jab Materiais Elétricos Ltda"
    assert extrair.matricula("2.227.500,00 m² (222,75 ha)") is None
    assert extrair.cartorio("MATRÍCULA 15.159 DO CARTÓRIO DE REGISTRO DE IMÓVEIS DE RODEIO BONITO") == "RODEIO BONITO"


def test_relatorio_html(tmp_path):
    from leiloes import relatorio

    l = leiloesjudiciais.ler_detalhe(_ler("lj_detalhe.html"), "https://x/lote/99790/218267", "pr")
    l.devedor = "Nome </script><b>teste</b>"
    arq = tmp_path / "r.html"
    assert relatorio.gerar([l], arq) == 1
    html = arq.read_text(encoding="utf-8")
    assert "__DADOS__" not in html and "Pinhão" in html
    assert "</script><b>" not in html  # dados não fecham o <script>
