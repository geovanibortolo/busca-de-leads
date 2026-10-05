from datetime import datetime
from pathlib import Path

from leiloes import extrair, planilha
from leiloes.fontes import leilaodefazenda as L

FIX = Path(__file__).parent / "fixtures"


def _detalhe(nome, mod="3"):
    html = (FIX / f"{nome}.html").read_text(encoding="utf-8", errors="ignore")
    return L.ler_detalhe(html, "https://exemplo/" + nome, "pr", mod)


def test_lista_traz_links_e_total():
    links, total = L.ler_lista((FIX / "ldf_lista_pr_judicial.html").read_text(encoding="utf-8", errors="ignore"))
    assert len(links) == 20
    assert total == 37
    assert all(l.startswith(L.BASE + "/imovel/") for l in links)


def test_detalhe_judicial():
    l = _detalhe("ldf_detalhe_judicial")
    assert l.modalidade == "Judicial"
    assert l.municipio == "Marechal Cândido Rondon"
    assert l.leiloeiro == "Giordano Leilões"
    assert l.area_ha == 29.5
    assert l.matricula == "49.854"
    assert l.ccir == "721.115.063.541-8"
    assert l.processos == ["0007010-10.2015.8.16.0112"]
    assert l.pracas == [(1, datetime(2026, 11, 19, 16, 0), 5776155.69)]
    assert l.link_edital.endswith(".pdf") and l.link_matricula.endswith(".pdf")


def test_detalhe_extrajudicial():
    l = _detalhe("ldf_detalhe_extrajudicial", "4")
    assert l.modalidade == "Extrajudicial"
    assert l.matricula == "25.828"
    assert l.cartorio == "Irati/PR"
    assert l.area_ha == 14.34
    assert [p[0] for p in l.pracas] == [1, 2]
    assert l.pracas[1][2] == 210177.01


def test_detalhe_partes_no_texto():
    l = _detalhe("ldf_detalhe_ampere")
    assert l.devedor == "LBR - LACTEOS VRASIL S/A"
    assert l.credor == "MARCON PNEUS TRANSPORTES LTDA"
    assert l.processos[0] == "1065066-76.2015.8.26.0100"


def test_area_usa_area_total_quando_em_m2():
    assert _detalhe("ldf_detalhe_outro", "5").area_ha == 68.36


def test_extratores_basicos():
    assert extrair.numero_br("1.234.567,89") == 1234567.89
    assert extrair.processos("Proc. 00070101020158160112") == ["0007010-10.2015.8.16.0112"]
    assert extrair.area_hectares("com 11 alqueires paulistas") == 26.62


def test_planilha(tmp_path):
    leiloes = [_detalhe("ldf_detalhe_judicial"), _detalhe("ldf_detalhe_extrajudicial", "4")]
    ref = datetime(2026, 10, 20)
    ativos = planilha.ativos(leiloes, ref)
    assert len(ativos) == 2
    assert planilha.ativos(leiloes, datetime(2026, 12, 1)) == []
    n = planilha.gerar(ativos, tmp_path / "x.xlsx", ref)
    assert n == 2 and (tmp_path / "x.xlsx").exists()
    assert planilha.prioridade(3) == "URGENTE"
