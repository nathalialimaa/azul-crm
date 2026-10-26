> Versão consolidada em 26/10/2026: veja [docs/CONSOLIDACAO.md](docs/CONSOLIDACAO.md) e o [pacote de pitch](docs/entrega-final-pitch/README.md). Resultados atuais: 213 testes passaram; API, oito páginas e pipeline ANAC verificados. O conteúdo abaixo registra a revisão anterior.

# Azul CRM — ajustes finais de 25/10/2026

Projeto privado. Estrutura Python, FastAPI, Streamlit, SQLite e contratos existentes preservados.
Veja `docs/REVISAO_FINAL.md` para mudanças, validação e lacunas perante o desafio.

## Executar no Windows

Extraia o ZIP em uma pasta nova e abra o PowerShell dentro de `azul-crm-develop`.
Use Python 3.12. Feche outras instâncias do aplicativo durante a preparação.

```powershell
py -3.12 -m venv .venv312
.\.venv312\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv312\Scripts\python.exe scripts/preparar_anac.py
.\.venv312\Scripts\python.exe -m streamlit run streamlit_app.py --server.address 127.0.0.1
```

O preparo utiliza os arquivos completos incluídos em `data/inputs/ANAC`, confere seus hashes,
importa aeroportos/tarifas/VRA, gera 400 clientes, treina e compara o churn, cria personas,
publica scores, auditoria e CLV, valida a base, indexa os documentos e exporta o lake em Parquet.
Pode consumir cerca de 2 GB de memória ou mais; reserve alguns GB livres em disco para banco e lake.
Não precisa de Snowflake nem Ollama para esse fluxo. O SQLite e os modelos são gerados localmente,
não estão empacotados. No Linux/macOS, use `python3 -m venv .venv` e `.venv/bin/python`.

**Execute o preparo apenas para gerar/regerar a demonstração:** ele limpa as decisões anteriores,
como o comando original `demo --public`. Nos próximos acessos, execute somente o comando Streamlit.
Não rode `demo` sem `--public` depois: isso trocaria a base calibrada pelas fixtures.
Se abrir o Streamlit antes do preparo, ele conserva o comportamento anterior: gera uma demo sem ANAC.
O preparo é local ao ZIP; publicar apenas o código no Git não transfere essa calibração.

Não é necessário criar `.env` para o modo local. Se reutilizar um `.env`, use:

```dotenv
CRM_STORAGE=sqlite
CRM_UI_MODE=local
RAG_PROVIDER=local
```

Para testar a API em outro terminal:

```powershell
.\.venv312\Scripts\python.exe -m uvicorn azul_crm.api.main:app --host 127.0.0.1 --port 8000
```

## Verificações

```powershell
.\.venv312\Scripts\python.exe -m pytest -q
.\.venv312\Scripts\python.exe -m ruff check .
.\.venv312\Scripts\python.exe scripts/verificar_base_conhecimento.py
```

## Ollama opcional

Instale/inicie o Ollama na máquina de apresentação e obtenha os modelos configurados:

```powershell
ollama pull embeddinggemma
ollama pull qwen2.5:3b
.\.venv312\Scripts\python.exe scripts/verificar_ollama.py
```

Se o serviço não estiver rodando, execute `ollama serve` em outro terminal. O diagnóstico faz
embeddings, indexação, busca e geração com referências. Só após passar, configure
`RAG_PROVIDER=ollama` no `.env` e reinicie o app. Confira o texto gerado manualmente.
O script não altera o `.env`, não baixa modelos e retorna código 1 se falhar. As mensagens de CRM
continuam vindo de templates mesmo nesse modo; o LLM é usado nas perguntas ao assistente.

## Dados incluídos

Os arquivos ANAC são exatamente os enviados. A lista de aeroportos foi obtida separadamente do
endereço OurAirports já usado pelo projeto; o hash é diferente da captura anterior de Larissa.
A nova procedência está em `data/inputs/ANAC/airports.source.json`. O guia original da Larissa
foi mantido nessa pasta como histórico; o roteiro acima descreve esta entrega.

Não envie este projeto para repositório público. Dados completos ficam ignorados pelo Git.
Vídeo, submissão, permissões do repositório e conferência manual de vigência não são tarefas
executadas por este código.
