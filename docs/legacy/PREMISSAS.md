# Premissas v1 — HAC-15

Versão de trabalho de 15/10/2026.

## Alto valor implementado

Fonte executável: `domain/scoring.py`, parâmetros em `config/settings.toml`.
Observação inclusiva: 01/10/2025 a 30/09/2026. Datas são datas civis ISO, sem fuso; não há timestamps de voos neste contrato.

- S = min(gasto / 18000, 1), gasto em BRL observado.
- F = min(frequência / 24, 1), uma linha de viagem corresponde a um trecho, não uma reserva ida e volta.
- R = max(0, 1 - recência / 180).
- Value Score = round(100 × (0,5S + 0,3F + 0,2R), 2).
- Alto valor: score >= 70. Não usamos percentil/top 20% nesta versão.

Os pesos, referências e limiares são configuráveis. R$18 mil, 24 trechos, 180 dias e 70 pontos são hipóteses demonstrativas; não foram estimados a partir de clientes reais. A normalização é por referências fixas, sem ajuste na amostra de teste. Empates em prioridade são ordenados por customer_id.

Sem viagem observada: gasto=0, frequência=0, incident_rate=0 e recency_days=tamanho inclusivo da janela (365 no padrão). Zero incidentes aqui significa ausência de evidência, não satisfação comprovada. O score fica zero. Nenhum campo das tabelas atuais aceita nulo. Clientes sem atividade ficam fora do futuro treino de churn; não os rotular automaticamente como evadidos.

Fidelidade `DEMO_UNVERIFIED` não entra no score. Margem, influência, potencial futuro, saldo de pontos e CLV ainda não são calculados. CLV exige horizonte futuro, receitas, custos/margem e validação próprios.

## Risco atual implementado

incident_rate = viagens com atraso >=60 minutos / viagens observadas.
risco = round(min(0,95; 0,1 + 0,6 × min(recência/180; 1) + 0,25 × incident_rate), 4).
Essas constantes estão em `BaselineChurnPredictor`; não são parâmetros TOML nesta versão.
Risco alto: >=0,6, configurável no TOML. É um índice heurístico não calibrado, apesar do nome legado `RiskEstimate.probability` e do campo HTTP `churn_risk`.

Priority Score = round(Value Score × risco, 2).
Valor em risco = round(gasto observado × risco, 2): proxy demonstrativa em BRL, não receita futura perdida nem efeito causal.
Segmentos: alto valor/alto risco → Alto Valor em Risco; alto valor/baixo risco → Premium Leal; demais com alto risco → Reativação de Baixo Custo; demais → Lazer com Potencial. São quatro rótulos por regra; os nomes não comprovam lealdade ou intenção de lazer.

Exemplo: gasto=18000, frequência=24, recência=90 e incident_rate=0,2 produzem valor=90, risco=0,45, prioridade=40,50 e proxy em risco=8100.

## Churn futuro: contrato definido, geração e treino pendentes

| Decisão | Contrato v1 |
|---|---|
| População elegível | Clientes com pelo menos um trecho na observação |
| Observação | 01/10/2025–30/09/2026 inclusiva |
| Desfecho | 01/10/2026–31/03/2027 inclusiva, parametrizado no TOML |
| Evento de churn | Zero viagens na janela completa de desfecho |
| Rótulo | 1 se zero viagens, 0 se pelo menos uma; não usar caso com janela incompleta |
| Sem atividade observada | Excluir da população de treino; acompanhar separadamente |
| Baseline | Índice atual; classificação >=0,6 |
| Recursos do modelo | Somente informações disponíveis até o corte |

A hipótese de seis meses pode confundir viagens sazonais com evasão; avaliar por frequência/perfil antes de alegar utilidade real. As datas futuras são simuladas, não observações reais já disponíveis.

Especificação para HAC-8: amostrar propensão com recência, incidentes, frequência, variável latente independente e ruído; usar transformação logística e sorteio Bernoulli reproduzível. Se evadir, gerar zero viagens futuras; caso contrário, uma ou mais. Derivar o rótulo da atividade futura. Coeficientes, distribuição do ruído e calibração ainda serão definidos e versionados em HAC-8. Não copiar o limiar do baseline para fabricar o rótulo. Não incluir propensão latente nem atividade futura nas features.

Especificação para HAC-21: separar treino/teste por cliente, ajustar transformações somente no treino, comparar baseline e modelo em ROC-AUC, PR-AUC, precisão/recall e calibração. Métricas sintéticas não comprovam desempenho real. Não há labels, modelo treinado ou SHAP nesta entrega.

## Como confirmar

1. Rodar `python -m azul_crm.pipeline.cli demo` e `python -m azul_crm.pipeline.cli validate`.
2. Rodar `python -m pytest -q`.
3. Consultar `/api/v1/metadata`: pesos, janela, método de risco e status do desfecho.
4. Revisar este documento e os parâmetros. Alteração na observação exige regenerar a Gold; após qualquer mudança, reiniciar a API. Mudanças nos pesos alteram scores em tempo de consulta, não os CSVs de features.
5. Registrar no PR o aceite técnico e eventual revisão pendente. Testes confirmam implementação, não validade de negócio das hipóteses.
