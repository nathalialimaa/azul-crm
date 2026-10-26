# Gemini no Azul CRM

O Gemini é o provedor de geração de texto. A integração usa o endpoint REST oficial, com chave somente no header enviado pelo servidor. Ollama não foi instalado nem ativado nesta versão.

## Configuração e uso

No `.env` local ou no ambiente privado da Vercel: `GEMINI_API_KEY`, `GEMINI_MODEL=gemini-3.8-flash`, `GEMINI_MAX_ATTEMPTS=1`. Reinicie o processo após mudar o `.env`; variáveis já definidas no sistema têm precedência.

A versão web chama o modelo apenas quando a pessoa pressiona **Perguntar** ou **Gerar novo texto com Gemini**. Abrir telas, filtrar, criar prévia do playbook, analisar sentimento e registrar aprovação não chama o Gemini.

| Proteção da versão web | Comportamento |
|---|---|
| Cota | `GEMINI_DAILY_LIMIT=5` por padrão; global, por dia UTC |
| Reserva | Atômica antes da chamada; falhas também contam |
| Intervalo | 20 segundos entre reservas globais |
| Retentativa | Uma tentativa; sem repetição automática |
| Cache | Respostas JSON bem formadas reutilizadas por 20 minutos para o mesmo contexto/pergunta/modelo |
| Persistência | SQLite local ou Redis REST compartilhado na Vercel |
| Indisponibilidade de estado | Geração bloqueada antes de chamar o Google |

O modelo recebe indicadores calculados, ação elegível e evidências versionadas. Ele explica e redige; não calcula CLV, risco ou elegibilidade. Rascunhos com ação alterada, citações inválidas, números ou promessas de benefício são bloqueados. Validação estrutural não garante fidelidade semântica; revisão humana continua necessária.

Respostas locais em contingência são identificadas como `structured_fallback`, e mensagens do playbook como `playbook_template`. Não são apresentadas como geração do Gemini. Nenhuma campanha é enviada.

## Estado da verificação

Na revisão da versão web, foi feita **uma única chamada real** com a nova chave. O provedor respondeu **HTTP 503**. Não houve retentativa nem chamadas adicionais para tentar contornar a indisponibilidade. O modelo configurado foi preservado conforme solicitado. A chave não foi versionada.

As evidências históricas da integração anterior permanecem em `docs/evidencias/gemini`; elas não substituem o resultado mais recente em `docs/evidencias/web/validacao.json`. Disponibilidade e cotas dependem do Google. HTTP 503 indica indisponibilidade; HTTP 429 indica cota do provedor. Trocar a chave não garante que esses erros desapareçam.

## Verificação controlada

A suíte usa transporte simulado e não exige credenciais. Para uma verificação manual explícita, use `python scripts/verificar_gemini.py --real`. O script faz no máximo uma chamada, passa pelo mesmo contador da interface web e salva apenas status sanitizado em `.runtime/gemini-check.json`. Nunca o coloque no CI nem execute em laço.

O ambiente analítico Streamlit preservado usa o adaptador compartilhado, com uma tentativa por padrão. A cota compartilhada e o cache descritos acima pertencem à API da nova interface web. Para demonstração e publicação, utilize a versão web em `web/`.

Fontes: [GenerateContent](https://ai.google.dev/api/generate-content), [saídas estruturadas](https://ai.google.dev/gemini-api/docs/structured-output). Publicação: [Vercel](VERCEL.md).
