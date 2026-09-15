# AGENTS.md — travel-tracker

Monitor diário de preços de viagem (passagens + hospedagem) com alerta Telegram só em deal. Cron no VPS; Chrome headless dedicado; baseline estatístico próprio.

## Start here

- Entrypoint do projeto: [skills/travel-tracker/SKILL.md](skills/travel-tracker/SKILL.md) · [manual visual](skills/travel-tracker/README.html)
- Invocação: `/travel-tracker <cmd>` — cmds: `add-watch`, `tick`, `health`, `status`

## Skills & workflows

| Cmd | O que faz | Manual |
|---|---|---|
| add-watch | adiciona destino/data ao monitor | [README](skills/travel-tracker/workflows/add-watch/README.html) |
| tick | roda coleta agora (ops) | [README](skills/travel-tracker/workflows/tick/README.html) |
| health | diagnóstico + heartbeat | [README](skills/travel-tracker/workflows/health/README.html) |
| status | preços e histórico atual | [README](skills/travel-tracker/workflows/status/README.html) |

References: [routing-matrix](skills/travel-tracker/reference/routing-matrix.md) · [role-contracts](skills/travel-tracker/reference/role-contracts.md)

## Estado vivo

- **Fonte canônica de comportamento**: `probe.py` (coletor) + `watches.json` (monitores ativos)
- Por watch: `history/<slug>.jsonl` (1 obs/dia) · saúde em `health.json` · cooldown em `alerts.json`
- Skill Hermes global: `travel-tracker` (banner aponta pra cá como canônico)

## Constraints

- Silêncio por padrão: stdout vazio no tick = nada entregue no Telegram
- Alerta só se `< mediana30 −15%` (≥14 obs) ou `≤ target` do watch; cooldown 3 dias
- Google Flights: gate de 315 dias (fora disso watch dormant)
- Hotel: mediana dos listings SEM filtro de lixo; voo: min com filter_junk 20%
- Evidência real ou nada: obs de hotel registra `dates_flow_ok`; FAIL nunca sobrescreve último preço bom
- Repositório público: https://github.com/ggoldani/travel-tracker (commits em nome de Gold, sem assinatura de agente)
