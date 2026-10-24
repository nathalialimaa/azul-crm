# Índice dos documentos e premissas

Este índice diz qual documento responde a cada pergunta e reúne as **premissas assumidas**, que o
enunciado pede para documentar. Comece pelo `README.md`.

## Documentos

| Documento | O que responde |
| --- | --- |
| `ARQUITETURA.md` | Como o código está organizado em camadas, e os contratos da API |
| `CLV.md` | Como definimos CLV de 12 meses e alto valor, com margem, desconto e sensibilidade |
| `PERSONAS.md` | Como as personas são formadas, nomeadas e por que aeroporto, canal e tier ficam de fora |
| `PLAYBOOK.md` | A ação de cada persona e as proteções que impedem prometer benefício |
| `AUDITORIA_VIES.md` | Como medimos viés e como evitamos falso alarme, com taxas de erro |
| `MODELO_CHURN.md` | Quando o modelo de churn substitui a regra, e por que não substitui hoje |
| `BASE_DE_CONHECIMENTO.md` | O que o assistente consulta (incluindo o regulamento do Azul Fidelidade), como importar e verificar, e os limites da busca |
| `CALIBRACAO_PUBLICA.md` | Dados da ANAC: fontes, comandos, números e limites |
| `DATA_LAKE.md` | Camadas bronze, silver e gold em Parquet, dicionário de dados e DDL do Snowflake |
| `DEPLOY.md` | Docker, senha opcional e opções de hospedagem |
| `DEPENDENCIAS.md` | O que falta ativar: Snowflake, Ollama, MLflow |
| `VALIDACAO.md` | Matriz do que foi verificado e do que não foi |
| `DIAGNOSTICO_E_INTEGRACAO.md` | Diagnóstico e histórico da integração da versão 2 |
| `api/` | Contratos da API (OpenAPI e exemplos) |
| `legacy/` | Histórico da fase inicial. Não prevalece sobre os documentos acima |

## Premissas assumidas

Todas as premissas abaixo são **hipóteses de demonstração**, não dados da empresa, e podem ser
alteradas nos arquivos indicados.

| Premissa | Valor | Onde fica |
| --- | --- | --- |
| Clientes, fidelidade, resgates e desfechos | Sintéticos (400 clientes, seed 42) | `pipeline/extended.py` |
| Margem de contribuição do CLV | 15% da receita em dinheiro | `config/settings.toml`, seção `[clv]` |
| Taxa de desconto do CLV | 10% ao ano, fluxo no meio do horizonte | `config/settings.toml`, seção `[clv]` |
| Alto valor | 20% de maior valor potencial | `config/settings.toml`, seção `[clv]` |
| Risco alto (para "alto valor em risco") | Índice de risco de 0,6 ou mais | `config/settings.toml` |
| Persona "esfriando" | Média de 90 dias ou mais sem voar | `pipeline/personas.py` |
| Persona com atrasos | 50% das viagens com 60 min ou mais, ou 10% e 3 vezes a taxa média da base | `pipeline/personas.py` |
| Custo e retenção de cada ação | Hipóteses por ação | `config/playbook.toml` |
| Ofertas (bônus, upgrade, rota) | Hipóteses não verificadas, fora do texto da mensagem | `config/playbook.toml` |
| Auditoria de viés | Regra dos 4/5, significância com correção de Bonferroni (5% global), grupos de 30 ou mais | `pipeline/bias_audit.py` |
| Escolha do modelo de churn | Validação cruzada 5×3, ganho de AUC com t > 1,65 e Brier menor | `pipeline/modeling.py` |
| Atrasos calibrados | Distribuição do VRA da Azul no doméstico, por aeroporto com 200 voos ou mais | `pipeline/delays.py` |

## Dados reais usados

Apenas dados públicos da ANAC, e só quando ingeridos: tarifas aéreas domésticas e VRA. Veja
`CALIBRACAO_PUBLICA.md`. Nenhuma base, sistema ou credencial da empresa foi usada.
