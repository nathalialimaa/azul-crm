# Escolha entre o modelo de churn e a regra

O app tem duas formas de estimar o risco de evasão: uma **regra** (índice heurístico de recência e
atrasos) e uma **regressão logística** treinada com o desfecho simulado. A pergunta é quando trocar
a regra pelo modelo.

## Critério

O modelo só substitui a regra se **os dois** forem verdadeiros:

1. O ganho de AUC é **distinguível de ruído**: validação cruzada repetida (5 dobras × 3), em treino +
   validação (o teste fica de fora), com teste t pareado por dobra e a correção de Nadeau e Bengio
   para dobras que compartilham dados. É preciso `t > 1,65` (unilateral, 5%).
2. O Brier (calibração) do modelo é menor que o da regra.

O relatório (`artifacts/metrics.json`) traz o ganho médio, o erro-padrão e o `t`, além das métricas
no conjunto de teste. O teste **nunca** participa da escolha.

## Por que não "AUC maior na validação"

A regra antiga comparava as duas só na validação, com 80 clientes. Na mesma base, mudando apenas a
semente da divisão treino/validação/teste, ela promovia o modelo em **16 de 40 divisões (40%)**, e o
ganho médio no teste era de apenas +0,007 de AUC. A decisão dependia da sorte da divisão. Um corte
fixo de ganho (por exemplo, 0,01) também não resolve: com ganho real de +0,009, ele vira cara ou
coroa. O critério estatístico promove em **0 de 40** divisões, coerente com o ganho de +0,009 e
`t = 0,46`.

## O critério ainda adota o modelo quando ele é melhor

Por simulação (60 bases de 320 clientes):

| Situação | Modelo adotado |
|---|---|
| O desfecho depende de gasto e frequência, que a regra não usa | 60 de 60 |
| A regra já é a verdade | 0 de 60 |
| Desfecho aleatório | 1 de 60 |

## Limitações

- Desfechos sintéticos: a escolha vale para esta base, não para clientes reais.
- Com 320 clientes, só ganhos relativamente grandes passam no critério; é intencional.
- A regra e o modelo usam as mesmas quatro variáveis. Variáveis novas (tendência de frequência,
  cancelamentos) mudariam a comparação.
