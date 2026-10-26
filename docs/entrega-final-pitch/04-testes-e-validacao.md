> Integração Gemini/Flight Deck: veja [GEMINI.md](../GEMINI.md), [DESIGN.md](../DESIGN.md) e o [README atualizado](../../README.md). Os estados e limites mais recentes estão nesses guias.

# Testes e validação

Execute na raiz:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/export_contracts.py
.\.venv\Scripts\python.exe scripts/verificar_integracao.py
```

O último comando exige base preparada; inicia processos apenas em localhost, verifica saúde dos servidores, recomendações, fontes do assistente, gateway HTTP de sentimento e todas as páginas pelo AppTest. Encerra os processos que iniciou.

Resultados desta consolidação: [CONSOLIDACAO.md](../CONSOLIDACAO.md), [logs e ambiente](../evidencias/integracao/), [smoke.json](../evidencias/integracao/smoke.json).

Os testes novos verificam negação, abstenção, fontes, duplicação, limites de entrada, API/CLI de sentimento e mensagens limitadas com respostas de LLM simuladas. AppTest verifica funcionamento e controles; não substitui avaliação visual em navegador. Teste simulado de Ollama não comprova inferência real ou groundedness semântica.
