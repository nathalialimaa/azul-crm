# Guia para executar e demonstrar

## Preparar

Abra um terminal na pasta com `pyproject.toml`. Use Python 3.12:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe scripts/preparar_anac.py
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py --server.address 127.0.0.1
```

O preparo usa os dados públicos empacotados, recria a carteira sintética e limpa decisões anteriores desta cópia. Para uma base sem calibração pública, omita o preparo ANAC: a primeira abertura gera a demonstração automaticamente. O app não precisa de Node ou Snowflake para rodar localmente.

## Apresentar

1. Visão geral: identifique alto valor e clientes em risco.
2. Clientes: mostre viagens, fatores e fidelidade sintética.
3. Segmentos: explique as quatro personas e a definição de alto valor.
4. Ações de CRM: gere um rascunho e confira fontes/checklist; nenhuma mensagem é enviada.
5. Assistente IA: pergunte sobre metodologia e confira evidências.
6. Sentimento: clique em Analisar avaliações para usar o CSV sintético; mostre casos positivos, negativos, mistos e inconclusivos.
7. Dados e modelos: mostre método selecionado e dicionário do lake.

CLV é uma estimativa de valor com hipóteses de margem/desconto. Churn é risco de evasão. Persona é um agrupamento de comportamento. O simulador apresenta hipóteses, não efeito causal comprovado.

## Integrações opcionais

Ollama para composição limitada: `CRM_MESSAGE_PROVIDER=ollama`. Busca semântica exige também `RAG_PROVIDER=ollama`, modelos disponíveis e reconstrução do índice. A configuração padrão permanece local; veja [CONSOLIDACAO.md](../CONSOLIDACAO.md).
