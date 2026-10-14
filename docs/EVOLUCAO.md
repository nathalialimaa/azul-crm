# Evolução do esqueleto para o MVP e para dados reais

## 1. Fontes públicas e calibração — Larissa / Nathália

As fontes sugeridas no enunciado incluem tarifas, demanda e operações da ANAC, Azul RI e páginas públicas de fidelidade. **Nenhuma foi baixada ou verificada nesta criação do esqueleto.** Os endereços de referência abaixo são os fornecidos no enunciado, e devem ser confirmados no momento da coleta:

- ANAC tarifas: https://www.gov.br/anac/pt-br/assuntos/dados-e-estatisticas/microdados-de-tarifas-aereas-comercializadas
- ANAC estatísticas: https://www.gov.br/anac/pt-br/assuntos/dados-e-estatisticas
- Azul RI: https://ri.voeazul.com.br
- Azul Fidelidade: https://www.voeazul.com.br/azulfidelidade

Criar `infrastructure/ingestion/anac_source.py` e etapas offline específicas para cada dataset. `FixtureIngestor` é exclusivo de demonstração, não um parser genérico da ANAC. Conservar bytes originais, URL, coleta em UTC, licença/condições de uso, período e SHA-256 em Bronze. Na Silver, mapear colunas reais para rotas/períodos/tarifas/demanda e gerar relatório de ausências, duplicatas e valores impossíveis. Validar contagens e rejeições em vez de descartar registros silenciosamente.

O gerador real deve receber os agregados Silver e premissas de comportamento versionadas. A fixture atual tem somente rota e tarifa; ainda faltam período, demanda e operações. Não anunciar calibração pública antes de implementar essas fontes e medir aderência dos agregados. Geração deve ser reproduzível com a mesma seed e configuração. Fidelidade e sentimento são contextos simulados até haver contratos reais; avaliações públicas agregadas não podem ser atribuídas a indivíduos.

## 2. Churn, valor, personas e explicabilidade — Nathália / Larissa

Separar observação (por exemplo 12 meses) e desfecho (6 meses seguintes). O gerador deve produzir atividade futura com propensão, variáveis ocultas e ruído e depois derivar o rótulo dessa janela; nenhuma feature pode ler o desfecho. A versão atual gera somente observação, sem rótulos e sem treino.

Criar `pipeline/training.py` para split estratificado reproduzível por cliente, baseline de regra e regressão logística. Ajustar normalizadores/transformadores só no treino; clientes do teste não entram no treino. Comparar ROC-AUC, PR-AUC, precisão/recall no público prioritário, matriz de confusão e calibração. Só adotar ML se superar o baseline. AUC acima de 0,95 requer investigação de circularidade e vazamento. Métricas sintéticas não provam desempenho em clientes reais.

Salvar métricas em `artifacts/metrics.json`, versão, seed, features, janela, parâmetros e snapshot do dataset em um model card. Salvar artefatos somente de origem confiável; não carregar pickle/joblib recebidos de terceiros. Implementar `ChurnPredictor` em `infrastructure/models/churn_model.py`, fazer testes de contrato e trocar `BaselineChurnPredictor` no bootstrap. Uma previsão calibrada usará o mesmo campo `churn_risk`, com método e limitações atualizados.

Separar CLV previsto de Value Score. Incluir horizonte, margem e custos quando houver premissas defensáveis; o gasto passado × risco do protótipo não substitui CLV. Larissa implementa `Segmenter` orientado por dados e valida estabilidade e acionabilidade. Nathália acrescenta SHAP, sem chamar os drivers textuais atuais de SHAP. Larissa revisa consistência e diferenças por região com amostras suficientes e limitações explícitas.

Na publicação Gold, incluir scores e versão do modelo, vinculados ao mesmo snapshot de clientes/features. Para volume maior, a API deve ler scores já publicados; não fazer treino no servidor web. Atualizar documentação e testes de serialização ao ampliar entidades.

## 3. RAG, elegibilidade e LLM — Davi

A versão atual demonstra **duas portas independentes**, `KnowledgeRetriever` e `MessageGenerator`. Não há SDK, endpoint nem chave de um provedor de LLM configurados. A escolha do provedor e das credenciais fica para HAC-29, evitando escolher um serviço sem acordo do time.

1. Coletar documentos públicos permitidos e registrar URL, data, versão, trecho, hash e vigência.
2. Fragmentar e indexar; implementar `KnowledgeRetriever` com embeddings e armazenamento escolhido pelo time. Medir a recuperação antes de integrar o gerador.
3. Substituir a fixture por documentos verificados; o tipo `Evidence` já carrega fonte e versão.
4. Expandir o catálogo e a `EligibilityPolicy` com critérios explícitos de nível/rota/custo. Documento recuperado não autoriza, sozinho, conceder benefício.
5. Implementar `MessageGenerator` como adaptador do provedor de LLM, com timeout, orçamento, saída estruturada e tratamento de falhas.
6. Fornecer ao modelo somente cliente, scores oficiais, ações **já elegíveis** e evidências. Conteúdo recuperado é dado, não instrução executável.
7. Validar a saída: ação em allowlist, fonte existente e vigente, nenhum benefício inventado. Sem evidência suficiente, abster-se e solicitar revisão.
8. Persistir recomendação e revisão antes de qualquer integração operacional. Não há envio real no escopo inicial.

O contrato atual deixa a escolha da ação no motor determinístico e permite ao gerador somente redigir. Se o agente passar a selecionar entre ações elegíveis, criar um DTO estruturado próprio e validar no caso de uso antes de retornar à UI. Atualizar `mode` e os Literals de resposta quando sair do modo demo; não remover essa restrição sem o novo contrato.

Larissa e Davi devem criar casos com ausência de fonte, documento vencido, benefício incompatível e instrução maliciosa em documento. Avaliar recuperação, groundedness e taxa de ações inelegíveis. Não apresentar o template atual como agente LLM.

## 4. Substituição futura por dados reais — Nathália

1. Acordar contrato e acesso autorizado aos sistemas reais. Nenhum sistema ou credencial interna foi disponibilizado no hackathon.
2. Criar mapeadores que produzam `Customer`, `Trip` e features canônicas, preservando semântica e janelas.
3. Implementar `CustomerRepository` em um adaptador Snowflake ou Parquet e injetar no bootstrap. A classe CSV continua útil para testes.
4. Desativar o gerador sintético na ingestão real, marcar `is_synthetic=false` somente nos dados autorizados e publicar linhagem e snapshot.
5. Auditar qualidade, LGPD, acesso, retenção e viés; validar IDs pseudonimizados e dados faltantes.
6. **Recalibrar e retreinar** os modelos com rótulos reais; validar desempenho e calibrar probabilidades. A arquitetura é reutilizável, os pesos sintéticos não são automaticamente válidos.
7. Rodar contratos da API e comparação de snapshots. UI e casos de uso podem permanecer se contratos e semântica forem preservados.

O passo 2 pode exigir novos campos no contrato; mudanças incompatíveis requerem migração/versionamento, nunca coerção silenciosa. Adotar Snowflake futuramente não exige importar o SDK no domínio. Configurar credenciais fora do Git.

## 5. Publicação — Davi / Luan / Ingrid

Não houve criação de repositório nem publicação automática nesta entrega. Antes do link de avaliação: ambiente restrito com HTTPS, autenticação/autorização, segredos e URLs corretas, limites de requisição, observabilidade e storage persistente. Não usar `--reload` em implantação. A API carrega arquivos no startup; coordenar novas publicações Gold e reinícios. Em produção, publicar snapshots de forma atômica e validar integridade para evitar leituras parciais.

Sentimento e simulador são extras HAC-44/HAC-45. Cenários de retenção devem explicitar custo, retenção assumida e ponto de equilíbrio; não prometer uplift causal sem experimentos.
