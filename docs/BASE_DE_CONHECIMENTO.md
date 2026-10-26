# Base de conhecimento do assistente

A base reúne os textos em que o Assistente IA e as recomendações se apoiam. Fica em
`data/knowledge/`, com um arquivo JSON por documento, e cada documento guarda título, fonte, versão
e se é de demonstração.

## O que há na base

| Documento | Origem | Trechos | Uso |
| --- | --- | --- | --- |
| `catalogo-mvp-v2` | Interno (demonstração) | 1 | Regra de governança: o que o catálogo permite e o que não é autorizado sem regra pública |
| `metodo-mvp-v2` | Interno (demonstração) | 1 | Definição atual de alto valor, CLV, risco e limites |
| `fidelidade-regulamento` | Regulamento público do Azul Fidelidade | 48 | Consulta do assistente |

**O regulamento.** Versão `novo-2024`, em
`https://www.voeazul.com.br/br/pt/programa-fidelidade/regulamento/novo-2024`, copiada **manualmente**
em 23/10/2026 (47 mil caracteres). O último aditamento listado no próprio texto é de 28/02/2024. A
importação **não certifica a vigência**: confirme no site antes de qualquer uso real. O regulamento
proíbe coleta por robôs (item 14.20), por isso a captura foi manual e não deve ser automatizada.

O texto fica em repositório privado. Se o repositório um dia for público, remova esse documento.

## O que o regulamento diz e importa para o CRM

Os números entre parênteses são os itens do regulamento.

- **Níveis (12.1):** Básico, Topázio, Safira e Diamante, por pontos qualificáveis, trechos qualificáveis ou gasto aéreo. A qualificação zera todo ano, em 1º de janeiro (11.7).
- **Acúmulo (5.5.3):** 1 ponto a cada R$ 1,00 da tarifa, podendo variar conforme o nível.
- **Validade (6.1):** no mínimo 24 meses a partir do acúmulo.
- **Pontos Bônus (1.1.7):** são "dados mediante uma campanha promocional". O regulamento permite promoções por prazo determinado (14.7) e dá até 90 dias, depois do fim da campanha, para creditar (5.2 e 14.18).
- **Mudança de regras (12.5):** a Azul pode alterar regras e benefícios dos níveis com aviso prévio de 15 dias.
- **Comunicação (3.6):** o cadastro autoriza a Azul a enviar comunicação por e-mail, push, SMS e telefone, e a autorização pode ser revogada a qualquer momento. **Qualquer contato de CRM precisa respeitar esse consentimento.**

**O que o regulamento não define:** valores de bônus de uma campanha concreta, elegibilidade para uma cortesia de upgrade de cabine
e disponibilidade comercial. O item 12.1 e seus subitens trazem requisitos de qualificação
de nível; isso não autoriza uma cortesia de cabine, nem torna o tier sintético elegível. Por isso as ofertas do playbook seguem
como **hipóteses a validar** e nunca entram no texto da mensagem.

## Como as recomendações usam a base

A recomendação busca a **evidência de governança** (o que o catálogo autoriza) e, se não encontrar,
vira "revisão manual" e nada é sugerido. Com o regulamento na base, essa busca continua devolvendo o
trecho do catálogo primeiro; isso é conferido pelo script de verificação e por testes com bases
grandes (`tests/test_big_knowledge.py`).

Além da busca, toda recomendação traz um **checklist de revisão** cujo primeiro item cita o item 3.6
do regulamento (consentimento de comunicação). O texto do checklist é fixo no código e **não vem da
busca**; veja `docs/PLAYBOOK.md`.

## Como importar e verificar

```powershell
python -m azul_crm.cli document --file "C:\caminho\regulamento_fidelidade.txt" --document-id fidelidade-regulamento --title "Regulamento do Programa de Fidelidade da Azul (novo-2024, capturado em 23/10/2026)" --url "https://www.voeazul.com.br/br/pt/programa-fidelidade/regulamento/novo-2024"
python -m azul_crm.cli index
python scripts/verificar_base_conhecimento.py
python scripts/verificar_base_conhecimento.py "Qual a validade dos Pontos Azul?"
```

O script confere os documentos, a busca de governança, perguntas de exemplo, a abstenção e as
recomendações. Com perguntas como argumento, ele mostra as respostas dessas perguntas.

Versão (SHA-256 do arquivo importado): `0680d5256858796d8ed46100d332d089a743be71ee4b38cf75926e22104817ac`.

## Limites da busca

- A busca é **por semelhança de palavras** (TF-IDF), sem LLM. Ela não entende sinônimos: "Quando os pontos expiram?" não encontrou resposta, porque o regulamento usa "validade"; "Qual a validade dos pontos?" funciona melhor.
- Os trechos são janelas de palavras, e não cláusulas. Uma pergunta pode trazer um trecho vizinho ao certo. Leia o trecho e confira o número do item citado no texto.
- O assistente mostra os trechos encontrados, e não redige uma resposta. Sem trecho relevante, ele diz que não encontrou evidência suficiente.
- Para entender perguntas livres é preciso um modelo de linguagem ou de embeddings (modo Ollama), que existe no código e **nunca foi executado**.
