# CLV de 12 meses e definição de alto valor

O enunciado pede um score que combine **valor monetário, frequência, recência e potencial
futuro**, o valor do cliente ao longo do tempo (CLV) e não só o gasto acumulado. Esta é a
definição usada em toda a aplicação, com todas as premissas à vista.

## Definição

| Medida | Fórmula |
|---|---|
| **Valor potencial 12m** | gasto em dinheiro dos últimos 12 meses × margem × fator de desconto |
| **CLV 12m** | valor potencial × (1 − risco de evasão) |
| **CLV em risco** | valor potencial × risco de evasão |
| **Alto valor** | os 20% clientes de maior valor potencial (ranking exato, empate por id) |

O fator de desconto é `1 / (1 + taxa) ^ 0,5` (fluxo no meio do horizonte). O valor potencial é a
margem que o cliente deve gerar nos próximos 12 meses **se permanecer**; o CLV já desconta a
chance de ele sair.

## Como cada componente do enunciado entra

| Componente | Como entra |
|---|---|
| Valor monetário | gasto em dinheiro dos últimos 12 meses |
| Frequência | já está no gasto (mais viagens, mais gasto) e entra também no risco |
| Recência | entra no risco de evasão, que reduz o CLV esperado |
| Potencial futuro | horizonte de 12 meses, com margem, desconto e risco de evasão |

## Por que um percentil, e por que 20%

O corte é um **percentil da própria carteira**, não um número arbitrário: acompanha a base e dá
sempre o mesmo tamanho de grupo, mesmo quando os valores mudam. A fatia de 20% é uma convenção
(Pareto) e fica em `config/settings.toml` (`top_share`). A tela mostra a **concentração real**:
na base de demonstração os 20% mais valiosos concentram 41% do valor potencial, e os 10% e 30%
também são exibidos, para a escolha poder ser discutida.

## Premissas: são hipóteses

`margin` (15%) e `discount_rate` (10% ao ano) **não são dados da Azul**: estão em
`config/settings.toml`, na seção `[clv]`. A tela traz uma **tabela de sensibilidade** (margem de 5%
a 25% × desconto de 8% a 16%) com o CLV total em cada cenário.

**O que as premissas mudam e o que não mudam.** Margem e desconto multiplicam o valor de todos os
clientes da mesma forma. Elas mudam o **tamanho** do valor e do caso de negócio, mas **não quem é de
alto valor**: o ranking depende só do gasto. Há um teste automático para isso. Para o ranking mudar,
é preciso um modelo de frequência e ticket futuros (por exemplo, BG/NBD), o que exige dados reais.

## Relação com o resto

- `value_score` (0 a 100) continua sendo o score **operacional** de priorização (valor × risco).
  O CLV é a definição **econômica** de alto valor e de valor em risco.
- Os nomes "Fiéis de Alto Valor" e "Alto Valor Esfriando" das personas descrevem grupos de alto
  gasto e frequência. Na base de demonstração, todos os clientes do top 20% por CLV estão nesses
  dois grupos; a tela "Segmentos" mostra a composição por persona.
- A estratégia por persona e o simulador de cenário usam o **CLV em risco** (margem), e não mais
  a receita multiplicada pelo risco, que superestimava o valor.

## Como executar

```bash
python -m azul_crm.cli clv-report        # gera artifacts/clv_report.json
```

O `prepare` e o preparo do app já geram o relatório. Ele aparece na página **Segmentos**, no
endpoint `GET /api/v1/clv` e no lake (`gold.customer_value` e `gold.clv_assumptions`).

## Limitações

- Dados sintéticos: o resultado descreve o gerador, não clientes reais.
- Margem e desconto são hipóteses; o risco de evasão é um índice heurístico, não uma
  probabilidade validada.
- O gasto considera só receita em dinheiro: viagens pagas com pontos não entram.
- O horizonte é fixo em 12 meses.

## Com dados reais

Substituir o gasto passado por previsões de frequência e ticket (BG/NBD ou similar), calibrar a
margem por rota e classe tarifária com a área financeira, e validar o risco de evasão. A estrutura
(potencial, esperado, em risco, alto valor por percentil) permanece.
