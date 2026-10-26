# Azul CRM Intelligence · Web

Interface responsiva e API leve para Vercel. Usa a projeção sintética em `data/snapshot.json`, derivada do motor analítico do repositório.

**Documentação principal:** [README do projeto](../README.md). **Publicação:** [passo a passo Vercel](../docs/VERCEL.md).

Na raiz do repositório:

```powershell
python -m pip install -r web/requirements.txt
python -m uvicorn web.api.index:app --host 127.0.0.1 --port 8503
```

Na Vercel, selecione esta pasta (`web`) como Root Directory. Cadastre Gemini, senha, segredo da sessão e Redis REST conforme o guia. Nenhuma credencial está incluída nos arquivos versionados.

O frontend não chama o Gemini ao carregar: geração só por solicitação explícita. Cota inicial: 5 chamadas/dia, intervalo global de 20 s, cache de 20 min, sem retentativa automática. Estado local em SQLite; na Vercel, Redis externo obrigatório. A aplicação não envia campanhas.
