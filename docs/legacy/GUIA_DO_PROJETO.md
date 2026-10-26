# Entendendo o projeto

## Qual problema resolvemos?

A equipe de CRM precisa decidir quais clientes merecem atenção primeiro e que ação faz sentido para cada um. Só olhar quem gastou mais não mostra quem está deixando de voar. A proposta combina valor, risco, contexto e regras para apoiar essa decisão. Não existe acesso aos clientes reais da Azul no desafio: precisamos simular clientes, calibrando padrões de viagens com dados públicos.

Exemplo de uso: a analista abre a fila, escolhe um cliente valioso em risco, entende os fatores e recebe sugestão de contato com fontes. A decisão é humana; a aplicação não envia campanhas nem concede benefícios.

## Como funciona agora

1. `pipeline/cli.py`: executa o trabalho offline. Copia rotas fictícias para Bronze; normaliza na Silver; gera clientes/viagens e features na Gold; valida o resultado.
2. `bootstrap.py`: ao subir a API, valida a Gold, lê configurações e conecta os objetos.
3. `CsvCustomerRepository`: lê clientes e viagens do disco para memória.
4. `FeatureBuilder`: usa apenas viagens na observação e calcula gasto, frequência, recência e atrasos.
5. `CrmService`: coordena valor, risco, segmentos e prioridade. Scores são recalculados nas consultas, não treinados nem persistidos em CSV.
6. `api/routes.py`: recebe pedidos HTTP, chama serviços e devolve respostas validadas pelos schemas.
7. `frontend/api_client.py`: consulta a API; `frontend/app.py` desenha tabela, filtros, visão 360 e rascunho.
8. `RecommendationService`: procura fixture por palavras, aplica política de contato e usa template de texto. Isto demonstra a integração que depois receberá RAG e LLM.

RAG não precisa produzir todos os números do dashboard. Os números vêm dos dados/modelos; a recuperação de documentos serve para fundamentar as recomendações.

## Pastas e responsabilidades

| Pasta/arquivo | Papel | Exemplo de alteração |
|---|---|---|
| src/azul_crm/domain | Entidades, interfaces e regras puras | Alterar fórmula de valor ou regra de ação |
| src/azul_crm/application | Casos de uso e orquestração | Acrescentar dados à análise de cliente |
| src/azul_crm/infrastructure | CSV, configurações, conhecimento e validação | Trocar CSV por outro armazenamento |
| src/azul_crm/pipeline | Processamento offline | Integrar gerador calibrado |
| src/azul_crm/api | FastAPI, endpoints e respostas | Criar endpoint compatível com a UI |
| src/azul_crm/bootstrap.py | Escolha e ligação de implementações | Injetar predictor de ML no lugar do baseline |
| frontend | Streamlit e cliente HTTP | Mudar apresentação sem importar modelos |
| config | Pesos e datas | Testar hipótese de alto valor |
| data/fixtures | Entradas fictícias pequenas | Reproduzir demonstração |
| data/bronze, silver, gold | Saídas geradas | Inspecionar dados após o pipeline |
| docs, tests, .github | Contratos, verificações e CI | Evidenciar aceite técnico |

As interfaces em `domain/ports.py` permitem trocar repositório, modelo e gerador de texto sem reescrever a UI. Classes têm responsabilidades separadas e dependências são injetadas. Isso aplica POO e princípios SOLID; não significa que a arquitetura já esteja pronta para produção. A publicação não é atômica, não há autenticação, persistência de decisões nem otimização para grandes bases.

## Proximidade da proposta

| Proposta | Estado real |
|---|---|
| Organização Bronze/Silver/Gold | Funciona com fixtures |
| Dados públicos ANAC e calibração | Pendente |
| Base reproduzível | Existe, mas perfis são artificiais para demonstrar telas |
| Valor e priorização | Baselines funcionais, sem CLV preditivo |
| Churn e métricas | Índice por regra; ML e labels pendentes |
| Segmentação e explicabilidade | Quatro regras e drivers textuais; sem clustering/SHAP |
| API e dashboard | Fluxo funcional local |
| RAG e agente | Recuperação lexical fictícia + template; integração real pendente |
| Estratégia de retenção | Contato demonstrativo; catálogo comercial elegível pendente |
| Deploy, avaliação final e pitch | Pendentes |

O projeto é uma base integrada para desenvolver o MVP. Já permite entender a experiência final; ainda não demonstra os resultados analíticos e a IA previstos na proposta. Não apresentar risco como previsão validada, drivers como SHAP ou template como agente LLM.

## O que esta atualização mudou

Adicionou validação da Gold com falha explícita no pipeline/startup; removeu datas fixas do CLI em favor do TOML; verifica separação de observação/desfecho; expõe premissas em metadata; reforça validação de códigos de aeroportos; exporta contratos e exemplos; adiciona testes de dados inválidos e janelas; documenta fórmulas, schemas, governança, fontes e pendências. Não altera a fórmula original dos scores nem gera atividade futura ainda.

## Roteiro para explicar ao grupo

“Temos uma base Python com FastAPI no backend e Streamlit na interface. O pipeline gera dados fictícios organizados em camadas; a API calcula valor, risco por regras e prioridades; a tela permite explorar um cliente e gerar um rascunho. Agora os contratos, as hipóteses e a validação dessa base estão registrados. O próximo passo é calibrar a base com dados públicos e implementar churn treinado, explicabilidade e recomendações com documentos reais e LLM.”
