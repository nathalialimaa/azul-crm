# Explicação exata por valores de Shapley

A visão Clientes e `GET /api/v1/customers/{id}/explanation` explicam **os scores efetivamente ativos**, sem alterar a regra de promoção do modelo.

## Método

Quatro variáveis: gasto, frequência, recência e taxa de incidentes. Para cada saída, enumeramos as 16 coalizões. Ausência de uma variável significa substituí-la pelo valor da referência. A contribuição é a média ponderada das diferenças marginais, com peso `|S|! (n-|S|-1)! / n!`.

A referência é **uma única linha** com as médias de treino registradas em `artifacts/churn.json`. Sem esse artefato, usa a média das features observadas da carteira, sem consultar rótulos futuros. São valores de Shapley interventional com referência única; não é um explicador condicional nem uma instalação/execução da biblioteca `shap`.

A implementação por enumeração segue a formulação de Shapley; a [documentação oficial do ExactExplainer](https://shap.readthedocs.io/en/latest/generated/shap.ExactExplainer.html) descreve enumeração exata e mascaramento por background como abordagem para poucas variáveis.

## Saídas

- Valor da referência e score do cliente.
- Contribuição por variável nas unidades do score de valor ou do risco ativo.
- Erro de aditividade: referência + contribuições deve reconstruir o score.
- Versão do modelo, data contratual de avaliação e tipo de referência.

O risco pode continuar sendo heurístico. Explicar um índice não o transforma em probabilidade calibrada. Atribuições dependem da referência, e combinações mascaradas podem ser pouco representativas quando há correlação. Contribuições **não são efeitos causais**.

## Testes

`tests/test_explanations.py` verifica coeficientes conhecidos de modelo linear, variável sem efeito, simetria em interação e aditividade/equivalência com scores da API. `tests/test_customer_page.py` verifica o fluxo da página Clientes.
