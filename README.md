# Busca de leads – leilões de imóveis rurais

Coleta diária de imóveis rurais com leilão marcado (judicial e extrajudicial) e gera uma planilha priorizada pelo prazo até a última praça.

Foco inicial: **PR, SC e RS**.

## Uso

```bash
pip install -r requirements.txt
python -m leiloes                       # PR, SC e RS -> saida/leiloes_rurais_AAAA-MM-DD.xlsx
python -m leiloes --ufs PR --saida pr.xlsx
python -m leiloes --modalidades 3 4     # só judicial (3) e extrajudicial (4) no Leilão de Fazendas
python -m leiloes --fontes mega zuk     # só algumas fontes (fazendas, mega, zuk, judiciais)
python -m leiloes --sem-edital          # não baixa editais em PDF
```

Códigos de modalidade (filtro do site): `3` Judicial, `4` Extrajudicial, `5` Outro, `12` PGFN (Comprei), `8` Venda Direta, `11` Leilão SFI Caixa, `1` Venda Direta Online.
Padrão: `3 4 5`. Venda direta fica de fora porque o devedor já perdeu o imóvel.

Leilões cujas praças já passaram são descartados (use `--incluir-encerrados` para manter).

## Planilha

Aba **Leilões rurais**, ordenada por dias até a última praça:

- **Prioridade**: URGENTE (≤ 7 dias), ALTA (≤ 21), MÉDIA.
- Município, área (ha), datas e lances da 1ª e 2ª praça, avaliação.
- **Matrícula, cartório/comarca, CCIR (INCRA) e número do processo**, extraídos do texto do anúncio.
- **Devedor / executado** e **credor / exequente**: extraídos do anúncio ou, quando o anúncio não traz, do **edital em PDF** (coluna "Origem do nome"). Nem sempre é a parte do leilão (pode ser outra penhora na matrícula). Sempre conferir.
- **CPF/CNPJ citados** e **titular citado na matrícula** ("em nome de…", "Proprietário:").
- **Também anunciado em**: o mesmo imóvel (mesma matrícula e cartório) aparece em mais de uma fonte; fica uma linha só, com o registro mais completo.
- Links para o anúncio, edital e matrícula em PDF (abrir no navegador).

Aba **Resumo**: contagem por UF e modalidade.

## Fontes

| Fonte | Status |
|---|---|
| Leilão de Fazendas (leilaodefazenda.com.br) | ✅ agregador de dezenas de leiloeiros; filtro por estado e modalidade |
| Mega Leilões (megaleiloes.com.br) | ✅ categoria Imóveis Rurais por estado; autor/réu/processo estruturados |
| Portal Zuk (portalzuk.com.br) | ✅ vitrine rural + vitrines por estado (só a 1ª carga: o "carregar mais" é proibido no robots.txt) |
| Leilões Judiciais (leiloesjudiciais.com.br) | ✅ fazendas/sítios/chácaras por estado; edital em PDF lido automaticamente |

Observações:
- Editais em PDF só são lidos automaticamente onde o site permite (hoje: anexos do Leilões Judiciais). Leilão de Fazendas (anti-robô Cloudflare), Zuk e Mega (robots.txt proíbe o servidor de documentos) ficam como link na planilha para abrir manualmente. Quando o mesmo imóvel está em outra fonte, usa o edital de lá.
- Regras do robots.txt de cada site são respeitadas (ex.: Zuk proíbe `/edital` e rotas AJAX; Leilões Judiciais proíbe `?pagina=`).
- O coletor espera 1,5 s entre requisições e guarda cache de 20 h em `.cache/`.

## Testes

```bash
python -m pytest -q
```
