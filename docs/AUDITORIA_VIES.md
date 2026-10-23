# Auditoria de viés das recomendações

Pergunta central: **clientes com o mesmo comportamento (mesma persona) recebem o mesmo
tratamento, independentemente de aeroporto, região, canal ou tier?**

Esses atributos não entram no agrupamento das personas nem nos scores. A auditoria verifica se o
resultado final ainda os favorece ou prejudica, por exemplo por correlação indireta.

## Como executar

```bash
python -m azul_crm.cli personas
python -m azul_crm.cli sync-scores
python -m azul_crm.cli bias-audit        # gera artifacts/bias_report.json
```

Resultado na página **Auditoria de viés** do app e em `GET /api/v1/bias`. O relatório fica
marcado como desatualizado se a Gold mudar depois da auditoria.

## O que é medido

Resultado favorável = estar entre os **20% mais prioritários** da carteira (quem recebe atenção
de retenção). Para cada atributo:

| Lente | Medida | Alarme |
|---|---|---|
| Bruta | Taxa de seleção por grupo; razão menor/maior (regra dos 4/5) | razão < 0,8 |
| Controlada por persona | A mesma razão dentro de cada persona | razão < 0,8 em qualquer persona |
| Associação | Qui-quadrado persona × grupo e V de Cramér | p < 0,01 e V ≥ 0,2 |
| Oportunidade igual | Entre quem realmente saiu, proporção selecionada, por grupo | razão < 0,8 |
| Calibração | Risco previsto médio menos churn observado, por grupo | diferença ≥ 10 p.p. |

Grupos com menos de 30 clientes (20 dentro de uma persona) não são comparados e aparecem como
"amostra pequena".

## Vereditos

| Veredito | Significado |
|---|---|
| 🟢 OK | Sem disparidade bruta relevante |
| 🟡 Atenção | Há diferença bruta, mas ela some quando se compara a mesma persona (efeito do mix de personas) |
| 🔴 Alerta | Clientes da mesma persona têm tratamento diferente conforme o grupo |
| 🟠 Confundido | Há diferença bruta, não dá para comparar dentro da persona **e** o atributo praticamente determina a persona (associação relevante). Não afirma nem descarta viés |
| ⚪ Amostra pequena | Grupos pequenos demais, inclusive dentro de cada persona, para comparar com segurança |

## O que as bases sintéticas mostram

**Base de demonstração (rotas fictícias).** Canal e tier: OK. Aeroporto e região: **confundido**.
O gerador original atribui o perfil de comportamento pela posição do cliente, então o aeroporto
praticamente determina a persona (V de Cramér ≈ 0,78) e dois dos três aeroportos nunca entram no
top 20%. É um achado sobre o **gerador**, não sobre clientes reais.

**Base com rotas reais da ANAC** (`demo --public`, clientes sorteados pela demanda de assentos).
Canal e tier: OK. Região: **atenção** (a diferença bruta some quando se compara a mesma persona).
Aeroporto: **amostra pequena**: há dezenas de aeroportos e a maioria tem menos de 30 clientes, então
não dá para comparar com segurança. Com mais clientes por grupo a comparação passa a ser possível.

Nenhum dos dois cenários encontrou tratamento desigual dentro da mesma persona (nenhum alerta).

## Como evitamos falsos alarmes

A regra dos 4/5 sozinha **não serve** para grupos de algumas dezenas de clientes: com um atributo
sorteado ao acaso (sem nenhum viés), ela acusava alerta em **62% a 96%** das execuções. Por isso o
alerta exige três coisas, dentro da persona:

1. **Eventos suficientes:** pelo menos 10 clientes selecionados na persona; abaixo disso a razão não é
   comparada.
2. **Razão menor que 4/5**, como antes.
3. **Significância estatística:** teste exato de Fisher (2 grupos) ou qui-quadrado (3 ou mais), com
   correção de Bonferroni sobre as personas comparáveis do atributo (nível global de 5%).

Uma razão abaixo de 4/5 que pode ser acaso aparece como **inconclusivo** na tela, não como alerta.

Medido por simulação, com a estrutura de personas e as taxas de seleção da base:

| Cenário | Antes | Agora |
|---|---|---|
| Atributo aleatório (nenhum viés): alerta falso | 62% a 96% | 4% a 5% por atributo |
| Viés real de 10 pontos de prioridade para um grupo: detectado | n/d | 93% |
| Viés real de 15 pontos ou mais: detectado | n/d | 100% |

O que isso não cobre: um viés pequeno (cerca de 5 pontos) é detectado em só 26% das execuções, e
os testes assumem que os clientes são independentes. Com dados reais, auditar também com base legal
os atributos que não existem aqui (gênero, idade, raça).

## Limitações

- Dados sintéticos: o resultado descreve o gerador.
- A regra dos 4/5 é um alarme, não prova de discriminação nem de ausência dela.
- Só existem aeroporto, região, canal e tier. Gênero, idade e raça não existem na base; com dados
  reais, auditar também esses atributos, com base legal e tratamento adequado (LGPD).
- Recall e calibração usam o desfecho simulado, não churn real.
