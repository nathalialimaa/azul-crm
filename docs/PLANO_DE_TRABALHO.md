# Responsabilidades, fases e pontos de extensão

Fonte: `Sugestao_De_Sprints_Azul_Linhas_Aereas.md`, período **13 a 26/10/2026**. Este documento reproduz a divisão de trabalho das fontes, não confirma o estado atual das tasks no Linear. A estrutura técnica é ponto de partida; responsáveis revisam os contratos juntos na fase 1.

| Pessoa | Escopo e tasks | Onde começar neste repositório |
|---|---|---|
| Nathália | Gold e premissas HAC-6/HAC-15; gerador HAC-8; features HAC-19; valor HAC-20; churn HAC-21; SHAP HAC-22; prioridade HAC-24; substituição por reais HAC-39 | `domain/models.py`, `domain/scoring.py`, `application/features.py`, `pipeline/stages.py`, `docs/EVOLUCAO.md` |
| Larissa | Bronze HAC-16; perfilamento HAC-17; Silver HAC-18; validação HAC-9; dicionário HAC-10; personas HAC-23; consistência HAC-25; viés HAC-26; agente HAC-30 com Davi; clientes de demo HAC-35 | `pipeline/`, `domain/ports.py` (`Segmenter`), `tests/`, `docs/CONTRATOS.md` |
| Luan | Repo privado HAC-5; ambiente HAC-13; convenções HAC-14; ponta a ponta HAC-36; mentoria HAC-38; README HAC-40; roteiro HAC-41; vídeo HAC-42; submissão HAC-43 | `pyproject.toml`, `.github/`, `tests/`, README e roteiro da entrega |
| Davi | Contrato HAC-7 com Ingrid; regras públicas HAC-11; RAG HAC-27; elegibilidade HAC-28; agente HAC-29; endpoints HAC-31; deploy HAC-37; sentimento extra HAC-44 | `api/`, `domain/decisions.py`, `application/recommendations.py`, `infrastructure/knowledge.py`, `bootstrap.py` |
| Ingrid | Contrato HAC-7; layout HAC-12; cliente 360 HAC-32; interface do agente HAC-33; integração HAC-34; simulador extra HAC-45; apoio visual do pitch | `frontend/app.py`, `frontend/api_client.py`, schemas da API |

## Fases e aceites

| Prazo | Fase | Entrega esperada / critério de aceite |
|---|---|---|
| 14/10 | Setup e contratos | Todos rodam o fluxo local; Gold e API acordadas; repositório privado com revisão |
| 15/10 | Base pública intermediária | Larissa entrega Bronze/Silver reais e perfilamento; registra fonte, período e checksum |
| 16/10 | Gerador/layout | Nathália entrega gerador probabilístico; Ingrid mostra UI com contrato fictício |
| 17/10 | Base sintética | Calibração contra ANAC, features, validação e dicionário; Davi conclui coleta documental |
| 18/10 | Modelos | Valor, churn vs baseline, SHAP, segmentação e prioridade publicados |
| 19/10 | RAG/agente | Elegibilidade, recuperação e recomendação estruturada com fontes; auditoria de viés |
| 20/10 | Integração interna | Visão 360, UI do agente e teste ponta a ponta com clientes-exemplo; avaliação do agente |
| 21/10 | Protótipo por link | Davi publica ambiente restrito; mentoria de 21 a 23/10 |
| 23/10 | Pitch | Roteiro de Luan ajustado aos feedbacks |
| 25/10 | Entrega interna | README final, vídeo de até 5 minutos, revisão e congelamento |
| 26/10 | Submissão oficial | Envio pela plataforma dentro do prazo |

Caminho crítico: **Bronze → Silver → gerador → features → scores/modelos → API → dashboard → teste integrado**. Um bloqueio nessa sequência deve ser informado no mesmo dia. Os módulos de UI e recomendação podem evoluir com fixtures do contrato enquanto os modelos não estão prontos.

## Como dividir mudanças sem conflitos

- Nathália e Larissa acordam a Silver antes de alterar o gerador. Alterações de Gold precisam de PR com dicionário e exemplos atualizados.
- Davi e Ingrid revisam schemas e exemplos de resposta antes de mudar endpoints ou telas.
- Uma pessoa revisa cada PR antes do merge. Luan coordena integração diária; não concentra as implementações dos demais.
- Novos modelos ou adaptadores devem incluir teste do contrato correspondente. Nunca remover marcações de simulação para melhorar a apresentação.
- Não inserir chamadas a ANAC/LLM diretamente nas páginas nem no domínio. Injetar adaptadores pelo bootstrap.
- O esqueleto não marca HAC-XX como concluída: cada responsável verifica a implementação e o aceite no Linear.
