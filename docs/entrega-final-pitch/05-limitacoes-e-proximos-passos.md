# Limitações e próximos passos

## Por que existe

Evita que uma demonstração local seja apresentada como produto homologado e dá uma ordem segura para evoluir o MVP.

## Limitações atuais

- Clientes, fidelidade, resgates, comportamento e desfechos são sintéticos.
- Margem e desconto do CLV são hipóteses configuráveis.
- As explicações são contribuições lineares; SHAP não está implementado.
- O rascunho de ação usa template/playbook; Ollama real e groundedness não foram avaliados.
- O regulamento público importado não prova corpus oficial, vigência, autorização ou benefícios atuais.
- Snowflake, MLflow, hospedagem, acesso de avaliadores, vídeo e submissão não foram homologados.
- Sentimento público, autenticação de produção e controle de acesso de produção permanecem pendentes.
- AppTest valida execução/controles, não fidelidade visual pixel a pixel.

## Próximos passos seguros

1. Fazer smoke visual direcionado da página Clientes, sem repetir a suíte já verde.
2. Confirmar fontes e autorização do corpus com responsáveis, sem chamá-lo de oficial antes da prova.
3. Provar Snowflake/Ollama/groundedness em ambientes autorizados e separados do demo local.
4. Definir autenticação, acesso privado, vídeo e submissão com os responsáveis.
5. Atualizar a matriz e este pacote somente após nova evidência versionada.

## Como testar com segurança

Priorize fixtures sintéticas, ambiente local, comandos read-only quando possível e CI para a suíte completa. Nunca use credenciais de produção no repositório ou em comandos visíveis.
