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

## Limitações

- Dados sintéticos: o resultado descreve o gerador.
- A regra dos 4/5 é um alarme, não prova de discriminação nem de ausência dela.
- Só existem aeroporto, região, canal e tier. Gênero, idade e raça não existem na base; com dados
  reais, auditar também esses atributos, com base legal e tratamento adequado (LGPD).
- Recall e calibração usam o desfecho simulado, não churn real.
