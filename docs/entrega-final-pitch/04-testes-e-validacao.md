# Testes e validação

## Por que existe

Separa comandos reproduzíveis de resultados já registrados e define um smoke seguro, sem transformar esta etapa documental em nova execução pesada.

## Comandos reproduzíveis

Todos partem da raiz do worktree:

```powershell
cd C:\caminho\azul-crm
.\.venv\Scripts\python.exe -m azul_crm.cli validate
.\.venv\Scripts\python.exe -m azul_crm.cli demo --customers 400 --seed 42
.\.venv\Scripts\python.exe -m azul_crm.pipeline.cli demo
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src frontend tests
```

O CI registrado em [`../../.github/workflows/ci.yml`](../../.github/workflows/ci.yml) passou com Gitleaks, Ruff, 191 testes, demo, validação, exportação de contratos e preparo de clientes. Esses comandos não foram executados nesta etapa.

## Smoke visual seguro

1. Abra o Streamlit em `127.0.0.1`.
2. Confirme que o painel mostra clientes sintéticos, valor, risco e fila.
3. Abra um cliente e confira fatores e evidências.
4. Gere um rascunho, leia o checklist e confirme que nenhuma mensagem é enviada.
5. Troque filtros/segmentos e verifique estados vazios/erro.
6. Registre screenshot local sem dados sensíveis; não publique o protótipo.

## Critério de interpretação

Teste simulado, fixture sintética ou contrato HTTP não prova integração real. O resultado deve indicar comando, commit, ambiente, entrada e saída. Para o quadro completo, use [`../VALIDACAO.md`](../VALIDACAO.md).

## O que não foi executado

Nesta criação documental: suíte, Ruff, Docker, PDF e integrações externas não foram executados.
