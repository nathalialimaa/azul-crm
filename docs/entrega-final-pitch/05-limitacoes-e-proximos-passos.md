# Limitações e próximos passos

- Clientes, fidelidade e desfechos são sintéticos. Dados ANAC agregados não identificam clientes reais.
- CLV usa hipóteses de margem e desconto. Métricas de churn não demonstram desempenho com clientes reais.
- A explicação disponível é baseada em regras/contribuições lineares; SHAP não foi implementado.
- Sentimento é um baseline lexical sem corpus real rotulado; ironia e contexto podem causar erros. Não existe coleta automática de redes ou reclamações.
- LLM em mensagens escolhe abertura/encerramento do catálogo e usa o conteúdo factual do playbook. Não há redação livre nem inferência Ollama real comprovada nesta máquina.
- Regulamento público importado serve à consulta; vigência e benefícios não são certificados pelo software.
- Snowflake, MLflow, hospedagem privada, avaliadores, vídeo e submissão dependem de homologação externa.
- A API não possui autenticação de produção e deve permanecer em localhost na demonstração.

Próximo passo imediato: ler os originais do regulamento CRM de Alto Valor e proposta geral após o reenvio, complementar a matriz, implementar lacunas confirmadas e só então publicar a branch alternativa. [Consolidação](../CONSOLIDACAO.md).
