# Busca de leads – leilões de imóveis rurais

Coleta diária de imóveis rurais com leilão marcado (judicial e extrajudicial) e gera uma planilha priorizada pelo prazo até a última praça.

Foco inicial: **PR, SC e RS**.

## Uso

```bash
pip install -r requirements.txt
python -m leiloes                       # PR, SC e RS -> saida/leiloes_rurais_AAAA-MM-DD.xlsx
python -m leiloes --ufs PR --saida pr.xlsx
python -m leiloes --modalidades 3 4     # só judicial (3) e extrajudicial (4)
```

Códigos de modalidade (filtro do site): `3` Judicial, `4` Extrajudicial, `5` Outro, `12` PGFN (Comprei), `8` Venda Direta, `11` Leilão SFI Caixa, `1` Venda Direta Online.
Padrão: `3 4 5`. Venda direta fica de fora porque o devedor já perdeu o imóvel.

Leilões cujas praças já passaram são descartados (use `--incluir-encerrados` para manter).

## Planilha

Aba **Leilões rurais**, ordenada por dias até a 2ª praça:

- **Prioridade**: URGENTE (≤ 7 dias), ALTA (≤ 21), MÉDIA.
- Município, área (ha), datas e lances da 1ª e 2ª praça, avaliação.
- **Matrícula, cartório/comarca, CCIR (INCRA) e número do processo**, extraídos do texto do anúncio.
- **Partes citadas (devedor?/credor?)**: extração automática do texto; nem sempre é a parte do leilão (pode ser outra penhora na matrícula). Sempre conferir.
- Links para o anúncio, edital e matrícula em PDF (abrir no navegador).

Aba **Resumo**: contagem por UF e modalidade.

## Fontes

| Fonte | Status |
|---|---|
| Leilão de Fazendas (leilaodefazenda.com.br) | ✅ implementada |
| Mega Leilões, Portal Zuk, Leilões Judiciais | próximas |

Observações:
- Os PDFs de edital/matrícula do agregador ficam atrás de proteção anti-robô (Cloudflare); o coletor não contorna isso. Os links ficam na planilha para abrir manualmente.
- O coletor espera 1,5 s entre requisições e guarda cache de 20 h em `.cache/`.

## Testes

```bash
python -m pytest -q
```
