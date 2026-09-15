# travel-tracker.workflow.tick

## Goal
Executar a coleta diária de preços de forma segura e legível.

## Scope
- Aplica-se: execução manual/foreground, debug de coleta, força de re-coleta.
- Não cobre: interpretar se preço "é bom" (usar `status`).

## Triggers
- "roda agora", "coleta hoje", "por que não coletou?"

## Inputs
- opcional: `--only <slug>`, env `TT_FORCE=1` (pula dedupe)

## Invariants
- Modo cron (sem --once) imprime SOMENTE alertas; vazio = silêncio
- Dedupe antes do fetch; FAIL nunca sobrescreve último preço bom
- Hotel exige `dates_flow_ok:true`; sem isso o preço é da página genérica

## Procedure
1. `python3 probe.py --once` (foreground; imprime tudo).
2. Se watch específico: `--only <slug>`.
3. Debug de parsing: rodar testes (`python3 -m unittest test_probe`).
4. Nunca rodar com TT_FORCE em produção sem intenção explícita de duplicar obs.

## Outputs
- Stdout com ok/ALERTA/DORMANT/SKIP por watch; obs novas em history/

## Review gate
- [ ] Saída interpretada linha a linha
- [ ] ALERTA explicado (vs mediana30 ou target)

## References
- [../SKILL.md](../SKILL.md)
