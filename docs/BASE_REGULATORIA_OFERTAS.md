# Base documental das ofertas do playbook

Revisão do conteúdo já importado em 25/10/2026. Fonte: `data/knowledge/fidelidade-regulamento.json`,
versão SHA-256 `0680d5256858796d8ed46100d332d089a743be71ee4b38cf75926e22104817ac`, capturada
manualmente em 23/10/2026. Esta revisão NÃO confirma que o documento continua vigente no site.
A conferência manual da vigência permanece pendente. Nenhuma oferta foi promovida a `verified`.

| Código | Fundamentação no texto importado | O que NÃO fica autorizado |
|---|---|---|
| POINTS_BONUS | 1.1.7 define pontos bônus vinculados a campanha; 14.7 trata de promoções temporárias; 5.2 e 14.18 tratam do prazo de crédito. | Quantidade, prazo da campanha e elegibilidade da oferta proposta. Exige campanha aprovada e condições verificadas. |
| UPGRADE | 12.1 e subitens descrevem níveis e requisitos; 12.5 admite mudanças nos benefícios. 5.5.4 menciona upgrade de cabine como serviço adicional. | Menção ao serviço ou qualificação de nível não concede cortesia de cabine. Exige regra específica, disponibilidade e elegibilidade. |
| ROUTE_OFFER | Não foi identificada cláusula que autorize o desconto proposto para a rota favorita. | Preço especial ou desconto automático. Depende da área comercial e das condições tarifárias. |
| REVIEW_GESTURE | Não foi identificada cláusula que conceda a compensação proposta por atraso. | Prometer pontos, dinheiro ou benefício. Exige política própria e aprovação do Atendimento. |

Para todas as ações de contato, o checklist referencia 3.6: a autorização de comunicação pode ser
revogada. Marcar a caixa é uma confirmação humana na demonstração, não uma consulta a um cadastro
real de consentimento. Essa integração continua necessária antes do uso real.

O playbook escolhe o contato e mantém a oferta separada, como hipótese. A mensagem é produzida por
template, não contém a oferta e não é enviada. Aprovar registra a revisão com `sent=false`.

Correção da documentação anterior: o regulamento contém requisitos de qualificação dos níveis.
O que falta é autorização para a oferta específica e sua elegibilidade, não toda e qualquer regra
de qualificação. Níveis sintéticos não equivalem a status oficial do programa.
