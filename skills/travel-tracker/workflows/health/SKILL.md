# travel-tracker.workflow.health

## Goal
Diagnosticar a operação do tracker (coletas, falhas, entregas) e produzir o heartbeat.

## Scope
- Aplica-se: "tá quebrado?", falha de alerta, verificação pós-mudança.
- Não cobre: preços (usar `status`).

## Triggers
- "tá quebrado?", "não chegou alerta", "heartbeat"

## Inputs
- nenhum obrigatório

## Invariants
- 3+ fails consecutivos = estado crítico (deve ter gerado warning no canal)
- Watch com 0 obs = "semeando", não "ok"; dormant ≠ falha

## Procedure
1. `python3 probe.py --health` — relatório por watch.
2. Cruzar com `health.json` (fails, last_ok) e `probe.err.log`.
3. Se fail estrutural (DOM mudou): colher evidência ao vivo, abrir ciclo radioactive.
4. Heartbeat semanal é automático (cron Mondays 10h BRT) — não disparar manualmente sem necessidade.

## Outputs
- Relatório de saúde + diagnóstico de causa quando houver fail

## Review gate
- [ ] Todo watch não-ok tem causa nomeada
- [ ] Sem fail estrutural não tratado

## References
- [../SKILL.md](../SKILL.md)
