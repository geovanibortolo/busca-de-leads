"""Relatório HTML (arquivo único, abre no navegador, funciona offline).

Todo o conteúdo já vem montado no HTML, para aparecer mesmo em visualizadores
que não executam JavaScript (pré-visualização de apps no celular, por exemplo).
O script da página só acrescenta filtros, busca e o recálculo dos prazos.
"""

from datetime import datetime
from html import escape
from pathlib import Path

_MODELO = Path(__file__).with_name("relatorio.html")

GRUPOS = [
    ("URGENTE", "Esta semana", "Última praça em até 7 dias. Prioridade máxima de contato.", "var(--urgente)"),
    ("ALTA", "Próximas 3 semanas", "Última praça entre 8 e 21 dias.", "var(--alta)"),
    ("MÉDIA", "Mais adiante", "Última praça daqui a mais de 21 dias.", "var(--media)"),
    ("SEM DATA", "Sem data informada", "O anúncio não trouxe as datas das praças.", "var(--faint)"),
]


def _e(s):
    return escape(str(s if s is not None else ""), quote=True)


def _milhar(n):
    return f"{n:,.0f}".replace(",", ".")


def brl(v):
    return "—" if v is None else "R$ " + _milhar(v)


def num(v):
    if v is None:
        return ""
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s.rstrip("0").rstrip(",")


def _data(d):
    return d.strftime("%d/%m/%y · %H:%M")


def _resumo(texto, limite=700):
    return texto if len(texto) <= limite else texto[:limite].rsplit(" ", 1)[0] + " …"


def grupo_modalidade(m):
    m = (m or "").lower()
    if m.startswith("judicial"):
        return "Judicial"
    if m.startswith("extrajudicial"):
        return "Extrajudicial"
    if "pgfn" in m:
        return "PGFN"
    return "Outro"


def _dias(l, agora):
    ultima = l.ultima_praca
    if not ultima:
        return None
    return (ultima[1] - agora).days + (1 if (ultima[1] - agora).seconds > 0 else 0)


def _prioridade(dias):
    if dias is None:
        return "SEM DATA"
    return "URGENTE" if dias <= 7 else "ALTA" if dias <= 21 else "MÉDIA"


def _lance(l, agora):
    futura = next((p for p in l.pracas if p[1] >= agora), None)
    return (futura or (l.pracas[0] if l.pracas else (None, None, None)))[2]


def _cartao(l, agora):
    dias = _dias(l, agora)
    prio = _prioridade(dias)
    pracas = "".join(
        f'<div class="praca{" passou" if quando < agora else ""}">'
        f'<div class="n">{n}ª praça</div><div>{_data(quando)}</div><div class="v">{brl(valor)}</div></div>'
        for n, quando, valor in l.pracas
    )
    if l.devedor:
        origem = f" · fonte: {_e(l.devedor_fonte)}" if l.devedor_fonte else ""
        pessoa = (
            f'<div class="pessoa"><div class="rot">Devedor / executado · conferir{origem}</div>'
            f'<div class="nome">{_e(l.devedor)}</div>'
            + (f'<div class="extra">CPF/CNPJ citado: {_e(", ".join(l.documentos[:4]))}</div>' if l.documentos else "")
            + (f'<div class="extra">Credor / exequente: {_e(l.credor)}</div>' if l.credor else "")
            + "</div>"
        )
    else:
        dica = " — abra o edital ou a matrícula" if (l.link_edital or l.link_matricula) else ""
        pessoa = (
            f'<div class="pessoa vazia"><div class="rot">Devedor</div><div>Não informado no anúncio{dica}.</div>'
            + (f'<div class="extra">Credor / comitente: {_e(l.credor)}</div>' if l.credor else "")
            + (f'<div class="extra">Titular citado na matrícula: {_e(l.titular)}</div>' if l.titular else "")
            + "</div>"
        )
    fonte = l.fonte + (f" (+{len(l.tambem_em)} site{'s' if len(l.tambem_em) > 1 else ''})" if l.tambem_em else "")
    dados = [
        ("Matrícula", l.matricula and l.matricula + (f" · {l.cartorio}" if l.cartorio else "")),
        ("Processo", l.processos[0] if l.processos else ""),
        ("Avaliação", l.valor_avaliacao and brl(l.valor_avaliacao)),
        ("CCIR", l.ccir),
        ("Leiloeiro", l.leiloeiro),
        ("Fonte", fonte),
    ]
    dl = "".join(f"<dt>{k}</dt><dd>{_e(v)}</dd>" for k, v in dados if v)
    prazo = (
        '<div class="prazo MÉDIA"><b>?</b><span>sem data</span></div>'
        if dias is None
        else f'<div class="prazo {prio}"><b class="js-dias">{dias}</b><span>{"dia" if dias == 1 else "dias"}</span></div>'
    )
    tags = f'<span class="tag mod">{_e(l.modalidade or "Tipo não informado")}</span>'
    if l.area_ha:
        tags += f'<span class="tag">{num(l.area_ha)} ha</span>'
    if l.situacao:
        tags += f'<span class="tag">{_e(l.situacao)}</span>'
    botoes = f'<a class="btn principal" href="{_e(l.url)}" target="_blank" rel="noopener">Ver anúncio</a>'
    if l.link_edital:
        botoes += f'<a class="btn" href="{_e(l.link_edital)}" target="_blank" rel="noopener">Edital (PDF)</a>'
    if l.link_matricula:
        botoes += f'<a class="btn" href="{_e(l.link_matricula)}" target="_blank" rel="noopener">Matrícula (PDF)</a>'
    for t in l.tambem_em:
        nome, _, url = t.partition(": ")
        botoes += f'<a class="btn" href="{_e(url)}" target="_blank" rel="noopener">{_e(nome)}</a>'
    busca = " ".join(
        str(x) for x in (l.municipio, l.uf, l.devedor, l.credor, l.titular, " ".join(l.processos), l.matricula,
                         l.cartorio, l.titulo, l.leiloeiro, " ".join(l.documentos)) if x
    )
    ultima = l.ultima_praca[1].isoformat(timespec="minutes") if l.ultima_praca else ""
    return (
        f'<article class="cartao {prio}" data-uf="{_e(l.uf)}" data-grupo="{grupo_modalidade(l.modalidade)}" '
        f'data-dev="{1 if l.devedor else 0}" data-ultima="{ultima}" data-lance="{_lance(l, agora) or 0}" '
        f'data-area="{l.area_ha or 0}" data-busca="{_e(busca)}">'
        f'<div class="cab"><div><h3>{_e(l.municipio or "Município não informado")} / {_e(l.uf)}</h3>'
        f'<div class="onde">{_e(l.titulo)}</div></div>{prazo}</div>'
        f'<div class="tags">{tags}</div>'
        + (f'<div class="pracas">{pracas}</div>' if pracas else "")
        + pessoa
        + (f'<dl class="dados">{dl}</dl>' if dl else "")
        + (f'<details class="desc"><summary>Descrição do anúncio</summary><p>{_e(_resumo(l.descricao))}</p></details>'
           if l.descricao else "")
        + f'<div class="acoes">{botoes}</div></article>'
    )


def _barras(contagem, chave):
    maximo = max(contagem.values(), default=1)
    return "".join(
        f'<button class="barra" type="button" data-{chave}="{_e(k)}"><span>{_e(k)}</span>'
        f'<span class="trilho"><span class="cheio" style="width:{v / maximo * 100:.0f}%"></span></span>'
        f'<span class="q">{v}</span></button>'
        for k, v in sorted(contagem.items(), key=lambda kv: -kv[1])
    )


def _contar(itens, f):
    res = {}
    for l in itens:
        res[f(l)] = res.get(f(l), 0) + 1
    return res


def gerar(leiloes, caminho, agora=None):
    agora = agora or datetime.now()
    itens = sorted(
        leiloes,
        key=lambda l: (_dias(l, agora) if _dias(l, agora) is not None else 10**9, not l.devedor),
    )
    por_prio = {}
    for l in itens:
        por_prio.setdefault(_prioridade(_dias(l, agora)), []).append(l)

    secoes = ""
    for chave, titulo, texto, cor in GRUPOS:
        grupo = por_prio.get(chave, [])
        secoes += (
            f'<section class="grupo" data-prio="{chave}"{"" if grupo else " hidden"}><h2><span class="ponto" style="background:{cor}"></span>'
            f'{titulo} <span class="qtd">({len(grupo)})</span></h2><p>{texto}</p>'
            f'<div class="cartoes">{"".join(_cartao(l, agora) for l in grupo)}</div></section>'
        )

    urg = len(por_prio.get("URGENTE", []))
    alta = len(por_prio.get("ALTA", []))
    dev = sum(1 for l in itens if l.devedor)
    soma = sum(_lance(l, agora) or 0 for l in itens)
    area = sum(l.area_ha or 0 for l in itens)
    kpis = (
        f'<div class="kpi urgente"><div class="rot">Urgentes (≤ 7 dias)</div><div class="num">{urg}</div>'
        f'<div class="sub">+ {alta} com 8 a 21 dias</div></div>'
        f'<div class="kpi"><div class="rot">Com devedor identificado</div><div class="num">{dev}</div>'
        f'<div class="sub">{round(dev / max(len(itens), 1) * 100)}% dos leilões</div></div>'
        f'<div class="kpi"><div class="rot">Soma dos lances mínimos</div><div class="num">R$ {_milhar(soma / 1e6)} mi</div>'
        f'<div class="sub">próxima praça de cada imóvel</div></div>'
        f'<div class="kpi"><div class="rot">Área total</div><div class="num">{_milhar(area)} ha</div>'
        f'<div class="sub">quando informada no anúncio</div></div>'
    )
    ufs = sorted({l.uf for l in itens})
    fontes = ", ".join(f"{f} ({n})" for f, n in _contar(itens, lambda l: l.fonte).items())
    subtitulo = (
        f'{len(itens)} imóveis com leilão marcado em {", ".join(ufs)} · '
        f'dados coletados em {agora:%d/%m/%y} às {agora:%H:%M}'
    )
    chips = "".join(f'<button class="chip" type="button" data-uf="{u}" aria-pressed="false">{u}</button>' for u in ufs)

    html = (
        _MODELO.read_text(encoding="utf-8")
        .replace("__SUBTITULO__", _e(subtitulo))
        .replace("__KPIS__", kpis)
        .replace("__DIST_UF__", _barras(_contar(itens, lambda l: l.uf), "uf"))
        .replace("__DIST_MOD__", _barras(_contar(itens, lambda l: grupo_modalidade(l.modalidade)), "grupo"))
        .replace("__CHIPS_UF__", chips)
        .replace("__TOTAL__", str(len(itens)))
        .replace("__LISTA__", secoes or '<div class="vazio">Nenhum leilão encontrado.</div>')
        .replace("__FONTES__", _e(fontes))
        .replace("__GERADO__", agora.isoformat(timespec="minutes"))
    )
    Path(caminho).write_text(html, encoding="utf-8")
    return len(itens)
