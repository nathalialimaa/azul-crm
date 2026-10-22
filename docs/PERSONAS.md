# Personas orientadas por dados

Substitui, quando o artefato existe, a segmentação por regras de valor × risco (`RuleSegmenter`)
por grupos formados por KMeans sobre **comportamento observado**.

## Como executar

```bash
python -m azul_crm.cli demo --customers 400 --seed 42   # Gold nova (apaga personas antigas)
python -m azul_crm.cli train
python -m azul_crm.cli personas                        # --k 3 a 5 se quiser testar outro k
python -m azul_crm.cli sync-scores
```

Gera `artifacts/personas.json`. Sem ele a aplicação segue com as regras, e `/api/v1/metadata`
mostra `segmenter: rules`. Com ele, mostra `segmenter: kmeans_personas_v1`.

## Decisões técnicas

| Decisão | Motivo |
|---|---|
| Entram só variáveis de comportamento: gasto, frequência, recência, taxa de atraso e ticket médio | Persona descreve o que o cliente fez, não quem ele é |
| **Ficam de fora** canal preferido, aeroporto de origem e tier | Evita estereótipo e viés por atributo cadastral (LGPD / IA responsável). Lista gravada no artefato |
| Winsorização em p1–p99 antes de padronizar | Cliente extremo (por exemplo, tudo pago com pontos, gasto em dinheiro zero) formava um grupo de 1 pessoa |
| Grupo com menos de 5% da base barra a publicação | Grupo minúsculo é outlier, não persona |
| Nome definido por critérios explícitos | Valor acima/abaixo da média da base; "esfriando" se média ≥ 90 dias sem voar; "atrasos frequentes" se ≥ 50% das viagens com atraso ≥ 60 min |
| Artefato amarrado ao fingerprint da Gold | Gold diferente do treino faz a API falhar com mensagem clara, sem classificar com modelo velho |
| k = 4 por padrão | O enunciado pede 3 a 4 personas. A silhouette de k = 3, 4 e 5 fica no artefato para justificar a escolha |

## Qualidade medida (400 clientes sintéticos, seed 42)

Silhouette 0,41 · menor grupo 20% da base · estabilidade 0,98 (ARI médio em 10 reamostragens de 80%).

## Limitações

- Base sintética: os grupos refletem a estrutura do gerador, não comportamento real.
- Sem motivo de viagem, antecedência de compra ou diversidade de rotas, ainda não dá para
  separar corporativo de lazer. Quando essas variáveis existirem, basta acrescentá-las em
  `domain/personas.py` (`FEATURE_NAMES` e `persona_vector`) e rodar `personas` de novo.
- Com dados reais, treinar de novo e reavaliar nomes, estabilidade e viés antes de usar.
