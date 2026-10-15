# Azul CRM — base integrada e contratos da Sprint 1

Projeto privado do hackathon. Python + FastAPI + Streamlit. Dados fictícios, scores por regras e recomendação por template. **Ainda não há calibração ANAC, churn treinado, SHAP ou RAG com LLM.**

Comece por [Guia do projeto](docs/GUIA_DO_PROJETO.md), que explica o problema, as pastas e a distância até a proposta. Consulte [status da Sprint 1](docs/STATUS_SPRINT1.md), [schema Gold](docs/SCHEMA_GOLD.md), [premissas](docs/PREMISSAS.md), [API](docs/CONTRATOS.md), [fontes](docs/FONTES_FIDELIDADE.md) e [convenções](CONTRIBUTING.md).

## Rodar no Windows (PowerShell)

Extraia o ZIP. Abra o terminal **na pasta azul-crm que contém pyproject.toml**. Não copie uma venv de outra pasta: ambientes virtuais não são portáveis. Se atualizar sua pasta atual, preserve `.git` e a sua `.venv312`, substitua os arquivos do projeto e reinstale o pacote. Pare a API antes de regenerar dados. O ZIP não inclui dados gerados.

Se ainda não houver ambiente nesta pasta:
```powershell
py -3.12 -m venv .venv312
```

Instale e gere os dados (os comandos usam diretamente o Python correto e dispensam ativação):
```powershell
.\.venv312\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv312\Scripts\python.exe -m azul_crm.pipeline.cli demo --seed 42 --customers 40
.\.venv312\Scripts\python.exe -m azul_crm.pipeline.cli validate
.\.venv312\Scripts\python.exe -m pytest -q
```

Terminal 1, API:
```powershell
.\.venv312\Scripts\python.exe -m uvicorn azul_crm.api.main:app --reload
```
Abra http://127.0.0.1:8000/docs para testar os endpoints.

Terminal 2, também na raiz azul-crm:
```powershell
.\.venv312\Scripts\python.exe -m streamlit run frontend/app.py
```
Abra http://localhost:8501. Mantenha ambos os terminais abertos. Pare com Ctrl+C. O pipeline não precisa ficar aberto.

## Linux/macOS

```bash
python3.12 -m venv .venv312
source .venv312/bin/activate
python -m pip install -e ".[dev]"
python -m azul_crm.pipeline.cli demo
python -m azul_crm.pipeline.cli validate
python -m uvicorn azul_crm.api.main:app --reload
```
Em outro terminal, na mesma pasta, ative o ambiente e rode `python -m streamlit run frontend/app.py`.

## Ver e confirmar contratos

```powershell
.\.venv312\Scripts\python.exe scripts/export_contracts.py
.\.venv312\Scripts\python.exe -m ruff check .
```
`docs/api/openapi.json` contém os schemas HTTP; `docs/api/examples.json` contém requisições/respostas reais (inclusive 404 e 422). O script usa TestClient, não exige servidor ativo, mas precisa da Gold. Após modificar dados/configuração, regenerar exemplos e reiniciar a API.

## Usar a demonstração

1. Confira o aviso de simulação.
2. Veja a fila ordenada e filtre os segmentos.
3. Escolha um cliente na barra lateral.
4. Abra Cliente 360 e compare histórico e motivos dos scores.
5. Abra Recomendação e gere um rascunho. Nenhuma mensagem é enviada.

## Problemas comuns

| Sintoma | Solução |
|---|---|
| No module named azul_crm | Reinstalar com o mesmo python.exe usado para rodar |
| Gold ausente | Executar pipeline demo primeiro |
| Janela mudou ou Gold inválida | Parar API, conferir TOML, regenerar demo e validar |
| Dashboard não conecta | Conferir API na porta 8000; CRM_API_URL pode apontar para outro endereço |
| Porta ocupada | Encerrar processo anterior ou ajustar porta e CRM_API_URL |
| Comando streamlit/uvicorn não encontrado | Usar python.exe -m como acima |

A API carrega um snapshot em memória. Mudar CSV com API aberta não atualiza dados; reinicie. Os indicadores da UI representam até 500 clientes retornados, não toda uma base maior. Não há autenticação/deploy nesta versão; o acesso deve permanecer local até a etapa de publicação restrita.

[Validação desta entrega](docs/VALIDACAO.md) registra exatamente o que foi executado. O README anterior foi preservado para histórico, não é a fonte do status atual.
