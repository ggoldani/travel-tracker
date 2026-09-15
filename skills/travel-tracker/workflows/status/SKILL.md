# travel-tracker.workflow.status

## Goal
Responder "quanto está" e "como está a tendência" com evidência do histórico.

## Scope
- Aplica-se: consulta de preço atual, comparação GIG×GRU, evolução da série.
- Não cobre: operação do coletor (usar `tick`/`health`).

## Triggers
- "quanto tá?", "preço atual", "histórico", "tá barato?"

## Inputs
- opcional: slug do watch (default: todos os ativos)

## Invariants
- Preço citado SEMPRE do último obs ok (nunca de memória)
- Juntar 2 obs do mesmo dia = mesma coleta (dedupe)

## Procedure
1. Ler o último obs ok de cada watch: `tail -1 history/<slug>.jsonl`.
2. Contexto: baseline da obs (mediana30 ou seeding) e n.
3. Tendência: `python3 probe.py --health` + spark.png.
4. Para converter em decisão: comparar com `target` do watch, se houver.

## Outputs
- Tabela curta: watch · preço · Δ vs baseline · estado

## Review gate
- [ ] Nenhum preço citado sem obs correspondente
- [ ] Delta vs baseline explícito

## References
- [../SKILL.md](../SKILL.md)
