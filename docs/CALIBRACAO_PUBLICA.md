# Calibração com dados públicos da ANAC

A base é sintética, mas três partes dela são calibradas com dados públicos reais da ANAC. Cada
parte tem o seu arquivo, o seu comando e o seu limite.

| O que é calibrado | Fonte (ANAC) | Comando de ingestão |
|---|---|---|
| Tarifa média por rota | Microdados de tarifas aéreas domésticas (mensal) | `fares --file ... --period AAAA-MM` |
| Quantos clientes ficam em cada rota | Os mesmos microdados, assentos comercializados por rota | (mesmo arquivo) |
| **Atrasos** das viagens | Voo Regular Ativo (VRA), mensal | `vra --file ... --period AAAA-MM` |

Além disso, `airports` baixa a lista de aeroportos (OurAirports) usada para converter códigos ICAO
em IATA.

```powershell
python -m azul_crm.cli airports
python -m azul_crm.cli fares --file "...\anac_xxx.zip" --period 2026-09
python -m azul_crm.cli vra --file "...\VRA_20268.csv" --period 2026-08
python -m azul_crm.cli demo --public --customers 400 --seed 42
```

## Atrasos: o que muda

Sem o VRA, o gerador sorteia o atraso de cada viagem de uma lista arbitrária (0, 0, 30, 90 e 180
minutos), o que dá **40% das viagens com atraso de 60 minutos ou mais**. Com o VRA, cada viagem
recebe um atraso sorteado da distribuição **observada** da Azul no doméstico, por aeroporto de
origem quando há voos suficientes (200 ou mais) e no conjunto geral caso contrário. Antecipação
conta como zero de atraso.

Medido com o arquivo real de agosto de 2026 (Azul, doméstico, 22.969 voos realizados):

| Medida | VRA real | Viagens sintéticas |
|---|---|---|
| Atraso de 60 min ou mais | 2,9% | 2,7% |
| Atraso de 15 min ou mais | 12,1% | 11,7% |
| Cancelamentos | 1,3% dos voos programados | não modelados |

## O que isso muda no resto

- As personas deixam de ter um grupo de "atrasos frequentes" artificial. Pode aparecer um grupo
  pequeno com atraso **acima da média** (por exemplo, 19% das viagens, perto de 8× a taxa normal),
  que o playbook trata como recuperação de serviço.
- O risco de evasão deixa de ser puxado por atrasos inventados.

## Limites

- O VRA é de **um mês** (o mais recente com arquivo disponível), e as tarifas são de outro mês. A
  taxa de atraso varia pouco entre meses, mas isso não foi medido; o mês e o arquivo ficam
  registrados em `delay_calibration` no manifesto.
- Cancelamentos entram só como taxa no manifesto, não como viagens canceladas.
- Os atrasos são sorteados **por viagem, de forma independente**. Na realidade, o atraso de um
  cliente depende do horário, da época e da rota, e isso não é modelado.
- O comportamento do cliente (frequência, recência, resgate) continua vindo do gerador.
- O leitor do VRA rejeita e relata linhas sem data ou fora do período (0,03% no arquivo real) e
  recusa a carga se mais de 5% forem rejeitadas.
