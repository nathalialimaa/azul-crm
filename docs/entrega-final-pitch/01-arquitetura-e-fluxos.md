> Integração Gemini/Flight Deck: veja [GEMINI.md](../GEMINI.md), [DESIGN.md](../DESIGN.md) e o [README atualizado](../../README.md). Os estados e limites mais recentes estão nesses guias.

> Pacote integrado em 26/10/2026. Estado atual, novas funcionalidades e evidências: [Consolidação](../CONSOLIDACAO.md). As referências a commits e resultados de 25/10 abaixo são históricas.

# Arquitetura e fluxos

## Por que existe

Explica como uma demonstração local percorre domínio, dados, API e interface, e onde uma futura integração real poderia entrar sem afirmar que ela foi homologada.

## Camadas

```text
dados sintéticos + fontes públicas opcionais
        -> pipeline e validações
        -> SQLite local / lake Parquet
        -> CrmService e regras de domínio
        -> FastAPI ou gateway direto
        -> Streamlit: painel, clientes, segmentos, ações e assistente
```

- **Domínio:** entidades, pontuação, CLV, personas, elegibilidade e playbook em [`../../src/azul_crm/domain/`](../../src/azul_crm/domain/).
- **Aplicação:** orquestração de clientes, features, valor, risco e recomendações em [`../../src/azul_crm/application/`](../../src/azul_crm/application/).
- **Infraestrutura:** SQLite/Snowflake configurável, índice local, validação e armazenamento em [`../../src/azul_crm/infrastructure/`](../../src/azul_crm/infrastructure/).
- **Pipeline:** geração, ingestão pública, treino, personas, auditoria e exportação em [`../../src/azul_crm/pipeline/`](../../src/azul_crm/pipeline/).
- **Interface:** entrada [`../../streamlit_app.py`](../../streamlit_app.py), tela [`../../frontend/app.py`](../../frontend/app.py) e API em [`../../src/azul_crm/api/`](../../src/azul_crm/api/).

## Fluxos principais

1. **Preparar demonstração:** gerar clientes sintéticos, treinar/selecionar a regra, formar personas, calcular scores e validar Gold.
2. **Priorizar:** o painel combina valor potencial de 12 meses e risco de evasão para ordenar a atenção humana.
3. **Recomendar:** a aplicação recupera evidências locais e aplica o playbook; sem evidência, a ação é bloqueada/abstém-se.
4. **Revisar:** o operador confere evidências, consentimento e checklist; o sistema não envia mensagens.
5. **Consultar:** o assistente local extrativo mostra trechos do corpus; `RAG_PROVIDER=ollama` é caminho implementado, não execução comprovada.

## Como testar com segurança

Execute apenas o modo local com SQLite a partir da raiz. Mantenha a API em `127.0.0.1`, não use credenciais e não altere `CRM_STORAGE` para Snowflake. O detalhamento de configuração está em [`../ARQUITETURA.md`](../ARQUITETURA.md) e [`../DEPENDENCIAS.md`](../DEPENDENCIAS.md).
