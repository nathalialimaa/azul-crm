# Gemini no Azul CRM

## Decisão

Gemini foi integrado diretamente pelo endpoint oficial REST, aproveitando httpx já instalado. Não exige Ollama, download de modelos ou um gateway adicional. A API realmente respondeu com o modelo `gemini-3.8-flash` nesta conta. O catálogo listou `gemini-2.5-flash`, mas a geração foi recusada com aviso de indisponibilidade para novos usuários; por isso a configuração foi corrigida.

A escolha do modelo fica em `GEMINI_MODEL`. A disponibilidade/cota depende da conta. Consulte [geração de conteúdo](https://ai.google.dev/api/generate-content) e [saídas estruturadas](https://ai.google.dev/gemini-api/docs/structured-output).

## Configuração

No `.env` ignorado pelo Git: `GEMINI_API_KEY`, `GEMINI_MODEL=gemini-3.8-flash`, `CRM_LLM_PROVIDER=gemini`, `CRM_MESSAGE_PROVIDER=gemini`, `RAG_PROVIDER=local`. Reinicie o servidor após mudar variáveis. O aplicativo respeita variáveis de ambiente já definidas, sem sobrescrevê-las silenciosamente.

A chave não aparece em URL, frontend, status da API, logs ou exemplos. Ela é enviada no header `x-goog-api-key` somente ao host oficial. As configurações do VS Code usam o arquivo local, sem copiar a chave para launch.json/tasks.json.

## Funcionalidades

- Copiloto: indicadores computados da carteira, cliente selecionado, ação elegível e trechos versionados fundamentam uma resposta original.
- Mensagens: texto livre redigido pelo modelo, limitado por ação, fontes e proibição de promessas comerciais/números.
- Preview local: abrir um painel ou trocar filtros não dispara geração de mensagens. A chamada ocorre no botão de gerar.
- Auditoria: a aprovação reutiliza o rascunho mantido no serviço, sem gerar outra mensagem diferente durante o registro.
- Citações: resposta vazia, estrutura inválida, IDs desconhecidos e mensagens fora das restrições são recusados.
- Contingência: erro é sanitizado e exibido; os modos locais são identificados explicitamente.
- Retry: apenas erros 500/502/503/504, até três tentativas; 429 não provoca repetição automática.

O motor de regras continua responsável por elegibilidade. Esta integração não autoriza benefícios ou campanhas e não promete groundedness semântica comprovada.

## Verificação

`python scripts/verificar_gemini.py` faz duas chamadas reais e salva resultados sanitizados. `tests/test_gemini.py` testa estrutura, segredo no header, falhas, citações e preservação da revisão com transporte simulado. A suíte normal desativa geração externa implicitamente.

O serviço depende da disponibilidade e da cota Google. Se ocorrer indisponibilidade temporária, a interface informa isso e mantém os indicadores locais disponíveis.


O modelo 3.5 Flash também respondeu, mas apresentou HTTP 503 por alta demanda em parte das consultas. O 3.8 Flash foi testado e escolhido como principal. Mesmo assim, disponibilidade e cota externas não são garantidas pelo aplicativo.


## Latência e revisão concorrente

O cliente limita a janela total de tentativas a aproximadamente 45 segundos, com timeout por tentativa ajustado ao tempo restante. Modelos Gemini 3 usam `thinkingLevel=low`. O contexto é reduzido ao necessário. Cada rascunho tem ID único; a UI envia esse ID na decisão e o serviço rejeita rascunho expirado ou de outro cliente. Clientes HTTP antigos que omitem o ID mantêm compatibilidade com o último rascunho; integrações novas devem sempre enviá-lo. O cache é temporário, com até 500 rascunhos por instância.


## Resultado real desta revisão

A chave autenticou e houve geração estruturada de conexão com 3.8 Flash. Também foram observadas resposta fundamentada e mensagem original com 3.5 Flash, em chamadas separadas. Na validação completa mais recente, o Google retornou HTTP 503 por alta demanda. O teste da API Interactions estável retornou o mesmo erro. A execução completa com 3.8 não está sendo apresentada como homologada/estável. Veja `evidencias/gemini/resultado-final.json` e `validacao-real.json`.

O aplicativo está configurado para usar a API e informar claramente qualquer contingência. Resolver a disponibilidade do serviço Google não está sob controle do projeto. Não é necessário substituir a chave por causa de um 503; aguarde e tente novamente. Um 429 indica limite de uso e não provoca repetição automática.


A exportação tipada do lake inclui `draft_id` como coluna opcional em decisões: rascunhos novos preservam o identificador revisado, enquanto registros anteriores continuam aceitos sem esse campo. A regressão de CI que identificou esse contrato foi corrigida com teste ponta a ponta de Parquet.
