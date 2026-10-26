# Azul Flight Deck — direção visual

## Objetivo e identidade

O avaliador deve identificar rapidamente quem precisa de retenção, por quê e qual próximo contato preparar. A interface usa uma leitura inspirada em um centro de operação: azul-marinho no enquadramento, ciano em ações/realces e dados com contraste claro. O radar de retenção é o elemento central próprio do produto. Contagens e valores vêm da carteira, sem indicadores de crescimento inventados.

Tokens em `frontend/assets/theme.css`; componentes em `frontend/theme.py`. Fonte Manrope variável local, com licença OFL incluída, evitando dependência de fontes remotas durante a apresentação. O símbolo em mosaico e o wordmark são uma interpretação visual do protótipo, não um logotipo oficial fornecido pela companhia.

## Composição e estados

KPIs formam uma faixa de dados alinhados, sem ícones decorativos. Os painéis mantêm títulos claros, superfícies brancas e ações com foco visível. Navegação preserva labels e controles nativos acessíveis. O copiloto mostra fontes e o modo de geração. Carregamento, erro, contingência, aprovação bloqueada e ausência de dados permanecem identificáveis.

Breakpoints: 1100, 850 e 480 px. A faixa de quatro KPIs passa a duas colunas; os painéis empilham, as margens e títulos se adaptam e a navegação do Streamlit recolhe em telas pequenas. Tabelas mantêm scroll interno. Hover/foco e feedback usam transições leves; `prefers-reduced-motion` desativa movimento.

## Referências consideradas

- [taste-skill](https://github.com/Leonxlnx/taste-skill): adotadas orientação específica para app screens, hierarquia, dados honestos, acessibilidade e comparação visual. O repositório atual reúne os guias em taste-skill; várias URLs antigas de skills individuais enviadas não existem mais na árvore atual.
- [Impeccable](https://github.com/pbakaus/impeccable): polimento, adaptação, tipografia, estados e redução de elementos genéricos.
- [gstack](https://github.com/garrytan/gstack): critérios de revisão/consulta de design. Ferramentas iOS e fluxos específicos do ambiente Claude não se aplicam ao painel Python.
- [Huashu](https://github.com/alchaincyf/huashu-design): consultado; o próprio skill exclui sistemas produtivos com backend, portanto não foi usado como workflow obrigatório deste projeto.
- [Caveman](https://github.com/JuliusBrussee/caveman): estilo de comunicação de agentes, sem biblioteca de componentes para o app.
- [OmniRoute](https://github.com/diegosouzapw/OmniRoute): gateway de provedores que ainda exige contas/chaves. A integração direta Gemini evita um serviço extra e suas dependências na demonstração.

As referências são guias e ferramentas distintos, não um conjunto de bibliotecas compatíveis para instalar simultaneamente no Streamlit. A implementação segue um único sistema visual Azul e mantém a stack funcional existente.

## Verificação

Capturas de antes/depois em `docs/evidencias/design/`. A revisão verifica legibilidade, contraste, cabeçalhos, estados e funcionamento das páginas. As imagens documentam a aparência real, não um mockup gerado.


Revisão estática taste-skill: 0 falhas, 2 avisos de `box-shadow`. Ambos desenham segmentos sólidos do mosaico de marca e da faixa de cor, sem blur ou sombra de elevação. Inspeção real do navegador: fonte Manrope carregada, largura CSS de 1395 px e ausência de overflow horizontal. Depois dessa primeira inspeção, foram testados viewports reais de 390×844, 768×1024 e 1440×1000. Todos ficaram sem overflow horizontal. O teste em 768 px revelou uma faixa vazia causada pela largura mínima do menu recolhido; o seletor `data-collapsed=true` foi corrigido e o conteúdo passou a começar em x=0. As capturas mobile/tablet/desktop estão no diretório de evidências. O override de viewport foi removido ao terminar.


## Azul CRM Intelligence · versão web

A referência visual fornecida orientou a composição: sidebar azul-marinho, banner de aviação, superfícies claras, radar de retenção e cliente 360. Aplicamos a skill design-taste-frontend (tasteskill v2) na hierarquia de informações, consistência dos indicadores, tabelas, adaptação a 390/768/1440 px, foco visível e movimento reduzido. A preferência explícita pela imagem orientou as exceções de paleta, navegação saturada e banner em relação às regras genéricas dessa skill. Não foram instaladas bibliotecas incompatíveis apenas por constarem na lista de referências.

O banner `web/public/assets/aviation-banner.png` foi gerado com a ferramenta integrada de imagem e skill imagegen: fotografia panorâmica de asa de avião sobre nuvens ao pôr do sol, paleta marinho/ciano, espaço à esquerda para texto HTML, sem interface, pessoas, texto ou marca oficial. É uma ilustração gerada para a demonstração. O mosaico e o wordmark são uma interpretação visual do protótipo. A interface não usa a captura inteira como imagem: gráficos, filtros, tabelas e ações são elementos funcionais.

O cliente é identificado pelo código sintético. Não foram inventados nomes, retratos, pontuação de relacionamento, crescimento percentual nem probabilidade de sucesso para reproduzir os exemplos da referência. Todos os valores apresentados vêm da projeção do motor analítico. O radar usa índice de risco e valor potencial de margem; CLV líquido e valor potencial são identificados separadamente.
