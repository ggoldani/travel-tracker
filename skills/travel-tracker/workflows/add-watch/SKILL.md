# travel-tracker.workflow.add-watch

## Goal
Adicionar um novo monitor (voo ou hotel) ao tracker com semeadura imediata de histórico.

## Scope
- Aplica-se: novos destinos, novas janelas de datas, cross-check de origem.
- Não cobre: mudança de comportamento do coletor (usar ciclo radioactive).

## Triggers
- "monitora <destino>", "adiciona <rota>", "quero saber o preço de X"

## Inputs
- tipo (`voo`|`hotel`), origem/destino (IATA) ou cidade, datas ISO, `target` opcional (BRL)

## Invariants
- Slug único; datas ISO 8601; gate GF 315 dias → watch dormant acorda sozinho
- Nunca editar history à mão; semear é obrigatório (1ª obs no dia da criação)

## Procedure
1. Editar `watches.json` adicionando o watch (campos conforme tipo).
2. Rodar `python3 probe.py --once --only <slug>` (sem TT_FORCE; watch novo não tem obs hoje).
3. Confirmar obs criada em `history/<slug>.jsonl` com `ok:true` (ou DORMANT esperado).
4. Commit + push em nome de Gold.

## Outputs
- Entrada em watches.json · history/<slug>.jsonl semeado · commit pushed

## Review gate
- [ ] Slug único e datas ISO
- [ ] Primeira obs existe (ou DORMANT justificado com data de despertar)
- [ ] Commit pushed

## References
- [../SKILL.md](../SKILL.md) · [routing-matrix](../../reference/routing-matrix.md)
