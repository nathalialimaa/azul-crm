# Dados públicos da ANAC usados na calibração

> Documento interno do time. Não publicar, não usar em portfólio nem em trabalho acadêmico.

Esta pasta reúne os arquivos públicos da ANAC que **não vão para o Git** (ocupam uns 40 MB) e que
são necessários para reproduzir a base calibrada: tarifas, demanda por rota e atrasos reais.

## Arquivos desta pasta

| Arquivo (nome nesta pasta) | Nome original | O que é | SHA-256 |
|---|---|---|---|
| `anac_tarifa_setembro2026.zip` | `anac_211734935.zip` (DataSAS) | Tarifas aéreas domésticas comercializadas, **setembro de 2026** (contém `202609.CSV`) | `458f3b2e3d330c10517b69edc237b2a0351e0d879c01e006f6414cf361b1a1e4` |
| `VRA-agosto_2026.csv` | `VRA_20268.csv` (dados abertos) | Voo Regular Ativo (VRA), **agosto de 2026** | `2414e55a3baf16600462119192af3dcdc2775420942f997bc1b897d75a78392b` |
| `airports.csv` | `airports.csv` (OurAirports) | Lista de aeroportos, usada para converter ICAO em IATA | `0499dbd88de2fc735ac5c09f59796ccc3af544e17ffda807f793c0c6fe6c3d75` |

Os arquivos foram **renomeados** para ficarem claros na pasta. O conteúdo é idêntico ao original; se
quiser confirmar, compare o hash (abaixo).

**Origem dos arquivos**

- Tarifas: DataSAS da ANAC, tema "Tarifas Transporte Aéreo Passageiros Domésticos", ano 2026.
- VRA: portal de dados abertos da ANAC, "Voos e operações aéreas / Voo Regular Ativo (VRA) / 2026 /
  08 - Agosto", arquivo original `VRA_20268.csv`.
- Aeroportos: `https://davidmegginson.github.io/ourairports-data/airports.csv` (domínio público).

### Conferir os arquivos

Se o hash for diferente, o arquivo não é o mesmo e os resultados podem não bater.

```powershell
Get-FileHash "caminho\arquivo" -Algorithm SHA256
```

## Como reproduzir

Use a branch `feat/confiabilidade` (a mais recente da pilha) com o ambiente virtual ativo. Antes de
rodar, **defina a pasta onde estão os arquivos**. Troque o caminho do exemplo pelo caminho real:

```powershell
$dados = "C:\Users\SEU-USUARIO\Downloads\dados-anac"   # <-- TROCAR pelo caminho real
```

Depois, **um comando de cada vez**, esperando cada um terminar:

```powershell
python -m pip install -e ".[dev]"
python -m azul_crm.cli airports --file "$dados\airports.csv"
python -m azul_crm.cli fares --file "$dados\anac_tarifa_setembro2026.zip" --period 2026-09
python -m azul_crm.cli vra --file "$dados\VRA-agosto_2026.csv" --period 2026-08
python -m azul_crm.cli demo --public --customers 400 --seed 42
python -m azul_crm.cli train
python -m azul_crm.cli personas
python -m azul_crm.cli sync-scores
python -m azul_crm.cli bias-audit
python -m azul_crm.cli clv-report
python -m azul_crm.cli export-lake
```

- O passo `fares` é o mais pesado: de 1 a 3 minutos e uns **2 GB de memória**. Feche outros programas.
- A ordem importa. O `demo --public` apaga os modelos e as personas anteriores e gera tudo de novo,
  então `train`, `personas` e os seguintes precisam rodar depois dele.
- Se aparecer `No such file or directory ... C:\caminho\...`, o caminho ainda é o de exemplo.

Para ver o resultado no app:

```powershell
python -m streamlit run streamlit_app.py --server.address 127.0.0.1
```

## Resultados esperados

Com **os mesmos arquivos, a mesma lista de aeroportos e a mesma seed (42)**:

| Etapa | O que deve aparecer |
|---|---|
| `fares` | `rows: 892505`, `silver_rows: 892505`, `unmatched: 45` |
| `vra` | `rows: 88040`, `silver_rows: 87996`, `rejected_rows: 24` (todas `fora_do_periodo`) |
| `demo --public` | `calibration_scope: route_mean_fares_and_route_demand_and_delays` |
| Calibração de atrasos | 22.969 voos da Azul no doméstico; 2,94% com atraso de 60 min ou mais; 12,15% com 15 min ou mais; cancelamentos de 1,3% |
| `personas` | 4 grupos: 173 (Baixo Volume Ativo), 103 (Alto Valor Esfriando), 98 (Fiéis de Alto Valor) e 26 (Baixo Volume Ativo com Atrasos Acima da Média) |
| `train` | `selected: heuristic` (o modelo não supera a regra; `t` da validação cruzada abaixo de 1,65) |
| `bias-audit` | 0 alertas |
| `clv-report` | 80 clientes de alto valor (20%), concentrando 45% do valor; 37 deles em risco |

Pequenas diferenças numéricas podem aparecer com versões diferentes do `scikit-learn` ou do Python.
O que não deve mudar: o escopo da calibração, as contagens da ANAC e a conclusão qualitativa.

## O que esta pasta não resolve

- Isto reproduz a base **na máquina de quem rodar**. O link publicado do protótipo, se existir,
  sobe com a base de demonstração, **sem** a calibração real, porque estes arquivos não estão no
  repositório.
- Clientes, fidelidade, resgates e desfechos continuam **sintéticos**. A ANAC calibra só a tarifa
  média por rota, a distribuição de demanda por rota e os atrasos.
- Margem (15%) e taxa de desconto (10%) do CLV são hipóteses do time, não dados da Azul.

## Documentação relacionada (no repositório, pasta `docs/`)

- `CALIBRACAO_PUBLICA.md`: o que cada arquivo calibra e os limites.
- `CLV.md`: definição de CLV e de alto valor.
- `MODELO_CHURN.md`: por que a regra continua no lugar do modelo.
- `AUDITORIA_VIES.md`: como a auditoria evita falsos alarmes.
- `DATA_LAKE.md`: camadas em Parquet e dicionário de dados.
