# Convenções — HAC-14

Repositório privado. Não publicar desafio, dados ou resultados em redes sociais/portfólio.

1. Criar branch pelo código da tarefa: `git switch -c hac-6-contrato-gold`.
2. Commits pequenos: `feat(HAC-6): valida contrato Gold`; `docs(HAC-15): registra premissas`.
3. Rodar pipeline, validação, pytest e Ruff antes do PR.
4. PR deve dizer problema, mudança, testes, limitações e tarefa HAC relacionada.
5. Revisão por pelo menos outra pessoa antes do merge, conforme plano da equipe.
6. Como Nathália informou indisponibilidade dos colegas, pode preparar e testar estas mudanças. Se precisar integrar sozinha, registrar autorrevisão, motivo e revisão independente pendente no PR. Não afirmar aprovação que não ocorreu nem contornar proteção de branch.
7. Alteração incompatível de schema requer versão/migração. Atualizar exemplos pelo script e documentação no mesmo PR.
8. Não commitar .venv312, segredos ou dados volumosos. .env.example não deve conter credenciais.

Comandos de verificação:
```bash
python -m azul_crm.pipeline.cli demo
python -m azul_crm.pipeline.cli validate
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python scripts/export_contracts.py
```
Não há mudança automática no GitHub ou no Linear por executar esses comandos.
